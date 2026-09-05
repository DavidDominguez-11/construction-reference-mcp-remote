"""Regression tests for production bugs reported by Cloud Run.

Bug 1: NameError: name 'DISCLAIMER' is not defined
    — DISCLAIMER constant was missing from material_reference.py.

Bug 2: RuntimeError: Response content longer than Content-Length
    — JSONResponse(status_code=204, content=None) serialized None to b"null"
      (4 bytes) but 204 must have an empty body.
"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from construction_reference_mcp_remote.protocol.http_server import app
from construction_reference_mcp_remote.tools.material_reference import (
    DISCLAIMER,
    execute,
)

client = TestClient(app)


# ---------------------------------------------------------------------------
# Bug 1 regression: DISCLAIMER must be defined and used in execute()
# ---------------------------------------------------------------------------

class TestDisclaimerDefined:
    """Ensure the DISCLAIMER constant exists and is used by execute()."""

    def test_disclaimer_constant_is_a_nonempty_string(self) -> None:
        assert isinstance(DISCLAIMER, str)
        assert len(DISCLAIMER) > 0

    def test_execute_cement_returns_disclaimer(self) -> None:
        result = execute({"material_name": "cement"})
        assert result["disclaimer"] == DISCLAIMER

    def test_execute_alias_rebar_returns_disclaimer(self) -> None:
        result = execute({"material_name": "rebar"})
        assert result["disclaimer"] == DISCLAIMER

    def test_execute_default_location(self) -> None:
        result = execute({"material_name": "cement"})
        assert result["location"] == "Guatemala"


class TestExecuteResultSerializable:
    """Verify the success path returns a fully JSON-serializable dict."""

    def test_cement_is_json_serializable(self) -> None:
        result = execute({"material_name": "cement"})
        # This must not raise TypeError
        serialized = json.dumps(result, ensure_ascii=False)
        roundtrip = json.loads(serialized)
        assert roundtrip["material_name"] == "cement"
        assert roundtrip["disclaimer"] == DISCLAIMER

    def test_alias_rebar_is_json_serializable(self) -> None:
        result = execute({"material_name": "rebar"})
        serialized = json.dumps(result, ensure_ascii=False)
        roundtrip = json.loads(serialized)
        assert roundtrip["material_name"] == "reinforcing steel bar"

    def test_default_location_is_serializable(self) -> None:
        result = execute({"material_name": "sand"})
        roundtrip = json.loads(json.dumps(result))
        assert roundtrip["location"] == "Guatemala"


# ---------------------------------------------------------------------------
# Bug 2 regression: 204 response must have an empty body
# ---------------------------------------------------------------------------

class TestNotification204EmptyBody:
    """Verify that notifications/initialized returns a proper 204 with no body."""

    def test_204_has_no_content(self) -> None:
        resp = client.post(
            "/mcp",
            content=json.dumps({
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
            }),
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 204
        # Body must be empty — this is what caused the Content-Length mismatch.
        assert resp.content == b""


# ---------------------------------------------------------------------------
# HTTP-level regression: successful tools/call must return valid JSON-RPC
# ---------------------------------------------------------------------------

class TestToolsCallSuccessHTTP:
    """End-to-end HTTP test for a successful tools/call request."""

    def test_tools_call_cement_success(self) -> None:
        resp = client.post(
            "/mcp",
            content=json.dumps({
                "jsonrpc": "2.0",
                "method": "tools/call",
                "id": 100,
                "params": {
                    "name": "get_material_reference",
                    "arguments": {"material_name": "cement"},
                },
            }),
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 200
        data = resp.json()
        # Must be a successful JSON-RPC response (no "error" key).
        assert "error" not in data
        assert data["jsonrpc"] == "2.0"
        assert data["id"] == 100
        # Parse the tool result from the MCP content envelope.
        content = data["result"]["content"]
        assert len(content) == 1
        assert content[0]["type"] == "text"
        material = json.loads(content[0]["text"])
        assert material["material_name"] == "cement"
        assert material["disclaimer"] == DISCLAIMER
        assert material["location"] == "Guatemala"
        assert material["reference_price_range"]["currency"] == "GTQ"
