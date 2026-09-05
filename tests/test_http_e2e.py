"""End-to-end HTTP tests using the FastAPI test client.

These tests exercise the full stack: HTTP → JSON-RPC parsing → MCP handler → tool logic.
No Docker, Cloud Run, or network connection is required.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from construction_reference_mcp_remote.protocol.http_server import app

client = TestClient(app)


# ── Helper ──────────────────────────────────────────────────────────────────

def post_mcp(payload: dict | str | bytes, content_type: str = "application/json") -> dict:
    """Send a JSON-RPC request to POST /mcp and return the parsed response."""
    if isinstance(payload, dict):
        body = json.dumps(payload)
    elif isinstance(payload, str):
        body = payload
    else:
        body = payload
    resp = client.post("/mcp", content=body, headers={"Content-Type": content_type})
    return resp


# ── Health endpoint ────────────────────────────────────────────────────────

class TestHealthEndpoint:
    def test_returns_ok(self) -> None:
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


# ── Content-Type validation ────────────────────────────────────────────────

class TestContentType:
    def test_invalid_content_type_returns_415(self) -> None:
        resp = post_mcp('{"jsonrpc":"2.0","method":"initialize","id":1}', content_type="text/plain")
        assert resp.status_code == 415


# ── Invalid JSON ───────────────────────────────────────────────────────────

class TestInvalidJson:
    def test_malformed_json(self) -> None:
        resp = post_mcp("{bad json}", content_type="application/json")
        assert resp.status_code == 200
        data = resp.json()
        assert data["error"]["code"] == -32700  # Parse error

    def test_empty_body(self) -> None:
        resp = client.post("/mcp", content=b"", headers={"Content-Type": "application/json"})
        assert resp.status_code == 200
        assert resp.json()["error"]["code"] == -32700


# ── Invalid JSON-RPC ──────────────────────────────────────────────────────

class TestInvalidJsonRpc:
    def test_missing_jsonrpc_field(self) -> None:
        resp = post_mcp({"method": "initialize", "id": 1})
        data = resp.json()
        assert data["error"]["code"] == -32600  # Invalid Request

    def test_missing_method(self) -> None:
        resp = post_mcp({"jsonrpc": "2.0", "id": 1})
        data = resp.json()
        assert data["error"]["code"] == -32600


# ── Unknown method ─────────────────────────────────────────────────────────

class TestUnknownMethod:
    def test_returns_method_not_found(self) -> None:
        resp = post_mcp({"jsonrpc": "2.0", "method": "foo/bar", "id": 1})
        data = resp.json()
        assert data["error"]["code"] == -32601


# ── Initialize ─────────────────────────────────────────────────────────────

class TestInitialize:
    def test_initialize_response(self) -> None:
        resp = post_mcp({
            "jsonrpc": "2.0",
            "method": "initialize",
            "id": 1,
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "0.1.0"},
            },
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "result" in data
        result = data["result"]
        assert result["protocolVersion"] == "2025-06-18"
        assert "serverInfo" in result
        assert result["serverInfo"]["name"] == "construction-reference-mcp-remote"
        assert "tools" in result["capabilities"]


# ── notifications/initialized ──────────────────────────────────────────────

class TestNotificationsInitialized:
    def test_returns_204(self) -> None:
        resp = post_mcp({
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
        })
        assert resp.status_code == 204


# ── tools/list ─────────────────────────────────────────────────────────────

class TestToolsList:
    def test_returns_tools(self) -> None:
        resp = post_mcp({"jsonrpc": "2.0", "method": "tools/list", "id": 2})
        assert resp.status_code == 200
        data = resp.json()
        tools = data["result"]["tools"]
        assert len(tools) >= 1
        names = [t["name"] for t in tools]
        assert "get_material_reference" in names

    def test_tool_has_input_schema(self) -> None:
        resp = post_mcp({"jsonrpc": "2.0", "method": "tools/list", "id": 3})
        tool = resp.json()["result"]["tools"][0]
        assert "inputSchema" in tool


# ── tools/call — success ──────────────────────────────────────────────────

class TestToolsCallSuccess:
    def test_known_material(self) -> None:
        resp = post_mcp({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "id": 10,
            "params": {
                "name": "get_material_reference",
                "arguments": {"material_name": "cement"},
            },
        })
        data = resp.json()
        assert "result" in data
        content = data["result"]["content"]
        assert len(content) == 1
        material = json.loads(content[0]["text"])
        assert material["material_name"] == "cement"
        assert "isError" not in data["result"]

    def test_alias_lookup(self) -> None:
        resp = post_mcp({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "id": 11,
            "params": {
                "name": "get_material_reference",
                "arguments": {"material_name": "rebar"},
            },
        })
        material = json.loads(resp.json()["result"]["content"][0]["text"])
        assert material["material_name"] == "reinforcing steel bar"

    def test_price_range_present(self) -> None:
        resp = post_mcp({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "id": 12,
            "params": {
                "name": "get_material_reference",
                "arguments": {"material_name": "gravel"},
            },
        })
        material = json.loads(resp.json()["result"]["content"][0]["text"])
        pr = material["reference_price_range"]
        assert pr["currency"] == "GTQ"
        assert pr["minimum"] > 0
        assert pr["maximum"] >= pr["minimum"]


# ── tools/call — unknown material ─────────────────────────────────────────

class TestToolsCallUnknownMaterial:
    def test_returns_is_error(self) -> None:
        resp = post_mcp({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "id": 20,
            "params": {
                "name": "get_material_reference",
                "arguments": {"material_name": "unobtainium"},
            },
        })
        data = resp.json()
        assert data["result"]["isError"] is True
        assert "not found" in data["result"]["content"][0]["text"].lower()


# ── tools/call — missing params ───────────────────────────────────────────

class TestToolsCallMissingParams:
    def test_missing_tool_name(self) -> None:
        resp = post_mcp({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "id": 30,
            "params": {},
        })
        data = resp.json()
        assert data["error"]["code"] == -32602

    def test_unknown_tool_name(self) -> None:
        resp = post_mcp({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "id": 31,
            "params": {"name": "nonexistent_tool"},
        })
        data = resp.json()
        assert data["error"]["code"] == -32602

    def test_empty_material_name(self) -> None:
        resp = post_mcp({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "id": 32,
            "params": {
                "name": "get_material_reference",
                "arguments": {"material_name": ""},
            },
        })
        data = resp.json()
        assert data["error"]["code"] == -32602


# ── Default location behavior ─────────────────────────────────────────────

class TestDefaultLocation:
    def test_defaults_to_guatemala(self) -> None:
        resp = post_mcp({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "id": 40,
            "params": {
                "name": "get_material_reference",
                "arguments": {"material_name": "sand"},
            },
        })
        material = json.loads(resp.json()["result"]["content"][0]["text"])
        assert material["location"] == "Guatemala"

    def test_custom_location(self) -> None:
        resp = post_mcp({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "id": 41,
            "params": {
                "name": "get_material_reference",
                "arguments": {"material_name": "sand", "location": "Antigua"},
            },
        })
        material = json.loads(resp.json()["result"]["content"][0]["text"])
        assert material["location"] == "Antigua"
