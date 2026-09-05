"""Tests for the JSON-RPC 2.0 parser, validator, and response builders."""

from __future__ import annotations

import json

import pytest

from construction_reference_mcp_remote.protocol.jsonrpc import (
    JsonRpcInvalidRequest,
    JsonRpcParseError,
    error_response,
    is_notification,
    parse_request,
    success_response,
    validate_request,
)
from construction_reference_mcp_remote.protocol.errors import (
    INTERNAL_ERROR,
    INVALID_PARAMS,
    INVALID_REQUEST,
    METHOD_NOT_FOUND,
    PARSE_ERROR,
)


# ── Response builders ──────────────────────────────────────────────────────

class TestSuccessResponse:
    def test_minimal(self) -> None:
        resp = success_response(1, {"ok": True})
        assert resp == {"jsonrpc": "2.0", "id": 1, "result": {"ok": True}}

    def test_null_result(self) -> None:
        resp = success_response("abc", None)
        assert resp["result"] is None

    def test_string_id(self) -> None:
        resp = success_response("req-1", [])
        assert resp["id"] == "req-1"


class TestErrorResponse:
    def test_with_code_and_message(self) -> None:
        resp = error_response(1, PARSE_ERROR, "bad json")
        assert resp["error"]["code"] == PARSE_ERROR
        assert resp["error"]["message"] == "bad json"
        assert "data" not in resp["error"]

    def test_with_data(self) -> None:
        resp = error_response(2, INVALID_REQUEST, "oops", {"detail": "x"})
        assert resp["error"]["data"] == {"detail": "x"}

    def test_default_message(self) -> None:
        resp = error_response(None, METHOD_NOT_FOUND)
        assert resp["error"]["message"] == "Method not found"


# ── Parsing ────────────────────────────────────────────────────────────────

class TestParseRequest:
    def test_valid_json_object(self) -> None:
        body = json.dumps({"jsonrpc": "2.0", "method": "ping"}).encode()
        data = parse_request(body)
        assert data["method"] == "ping"

    def test_invalid_json(self) -> None:
        with pytest.raises(JsonRpcParseError):
            parse_request(b"{not json}")

    def test_json_array_rejected(self) -> None:
        with pytest.raises(JsonRpcParseError):
            parse_request(b"[1,2,3]")

    def test_empty_body(self) -> None:
        with pytest.raises(JsonRpcParseError):
            parse_request(b"")


# ── Validation ─────────────────────────────────────────────────────────────

class TestValidateRequest:
    def test_valid_request(self) -> None:
        validate_request({"jsonrpc": "2.0", "method": "initialize", "id": 1})

    def test_missing_jsonrpc(self) -> None:
        with pytest.raises(JsonRpcInvalidRequest):
            validate_request({"method": "initialize", "id": 1})

    def test_wrong_jsonrpc_version(self) -> None:
        with pytest.raises(JsonRpcInvalidRequest):
            validate_request({"jsonrpc": "1.0", "method": "x", "id": 1})

    def test_missing_method(self) -> None:
        with pytest.raises(JsonRpcInvalidRequest):
            validate_request({"jsonrpc": "2.0", "id": 1})

    def test_empty_method(self) -> None:
        with pytest.raises(JsonRpcInvalidRequest):
            validate_request({"jsonrpc": "2.0", "method": "", "id": 1})

    def test_invalid_params_type(self) -> None:
        with pytest.raises(JsonRpcInvalidRequest):
            validate_request({"jsonrpc": "2.0", "method": "x", "params": "bad"})

    def test_params_as_dict(self) -> None:
        validate_request({"jsonrpc": "2.0", "method": "x", "params": {"a": 1}})

    def test_params_as_list(self) -> None:
        validate_request({"jsonrpc": "2.0", "method": "x", "params": [1, 2]})


# ── Notification detection ─────────────────────────────────────────────────

class TestIsNotification:
    def test_with_id(self) -> None:
        assert not is_notification({"id": 1, "method": "x"})

    def test_without_id(self) -> None:
        assert is_notification({"method": "x"})

    def test_with_none_id(self) -> None:
        # JSON-RPC spec: id=null is technically a request, not a notification.
        assert not is_notification({"id": None, "method": "x"})
