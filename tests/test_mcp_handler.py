"""Tests for the MCP request handler dispatch logic."""

from __future__ import annotations

import json

import pytest

from construction_reference_mcp_remote.protocol.jsonrpc import (
    JsonRpcInvalidParams,
    JsonRpcMethodNotFound,
)
from construction_reference_mcp_remote.protocol.mcp_handler import handle_request


class TestHandleInitialize:
    def test_returns_server_info(self) -> None:
        resp = handle_request({
            "jsonrpc": "2.0",
            "method": "initialize",
            "id": 1,
            "params": {},
        })
        assert resp["result"]["serverInfo"]["name"] == "construction-reference-mcp-remote"
        assert resp["result"]["protocolVersion"] == "2025-06-18"


class TestHandleToolsList:
    def test_returns_tools(self) -> None:
        resp = handle_request({
            "jsonrpc": "2.0",
            "method": "tools/list",
            "id": 2,
            "params": {},
        })
        tools = resp["result"]["tools"]
        assert any(t["name"] == "get_material_reference" for t in tools)


class TestHandleToolsCall:
    def test_valid_call(self) -> None:
        resp = handle_request({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "id": 3,
            "params": {
                "name": "get_material_reference",
                "arguments": {"material_name": "cement"},
            },
        })
        content = resp["result"]["content"]
        assert len(content) == 1
        material = json.loads(content[0]["text"])
        assert material["material_name"] == "cement"

    def test_unknown_material_returns_is_error(self) -> None:
        resp = handle_request({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "id": 4,
            "params": {
                "name": "get_material_reference",
                "arguments": {"material_name": "unobtainium"},
            },
        })
        assert resp["result"]["isError"] is True


class TestHandleNotification:
    def test_initialized_notification_returns_none(self) -> None:
        resp = handle_request({
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
        })
        assert resp is None

    def test_unknown_notification_returns_none(self) -> None:
        resp = handle_request({
            "jsonrpc": "2.0",
            "method": "notifications/something_else",
        })
        assert resp is None


class TestHandleUnknownMethod:
    def test_raises_method_not_found(self) -> None:
        with pytest.raises(JsonRpcMethodNotFound):
            handle_request({
                "jsonrpc": "2.0",
                "method": "unknown/method",
                "id": 99,
            })
