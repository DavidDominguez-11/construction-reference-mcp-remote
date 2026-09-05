"""Manual JSON-RPC 2.0 parser, validator, and response builder.

This module does NOT use any MCP SDK.  It implements the subset of
JSON-RPC 2.0 required by the MCP lifecycle (initialize, notifications,
tools/list, tools/call) plus standard error handling.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from construction_reference_mcp_remote.protocol.errors import (
    ERROR_MESSAGES,
    INTERNAL_ERROR,
    INVALID_PARAMS,
    INVALID_REQUEST,
    METHOD_NOT_FOUND,
    PARSE_ERROR,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Response builders
# ---------------------------------------------------------------------------

def success_response(request_id: Any, result: Any) -> dict[str, Any]:
    """Build a JSON-RPC 2.0 success response."""
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": result,
    }


def error_response(
    request_id: Any,
    code: int,
    message: str | None = None,
    data: Any = None,
) -> dict[str, Any]:
    """Build a JSON-RPC 2.0 error response."""
    error: dict[str, Any] = {
        "code": code,
        "message": message or ERROR_MESSAGES.get(code, "Unknown error"),
    }
    if data is not None:
        error["data"] = data
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": error,
    }


# ---------------------------------------------------------------------------
# Parsing / validation
# ---------------------------------------------------------------------------

def parse_request(raw_body: bytes) -> dict[str, Any]:
    """Parse raw bytes into a JSON object.

    Raises ``JsonRpcParseError`` if the body is not valid JSON.
    """
    try:
        data = json.loads(raw_body)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise JsonRpcParseError(str(exc)) from exc

    if not isinstance(data, dict):
        raise JsonRpcParseError("Request body must be a JSON object")

    return data


def validate_request(data: dict[str, Any]) -> None:
    """Validate that *data* satisfies JSON-RPC 2.0 structural requirements.

    Raises ``JsonRpcInvalidRequest`` on failure.
    """
    if data.get("jsonrpc") != "2.0":
        raise JsonRpcInvalidRequest("Missing or invalid 'jsonrpc' field; must be '2.0'")

    method = data.get("method")
    if not isinstance(method, str) or not method:
        raise JsonRpcInvalidRequest("Missing or invalid 'method' field")

    params = data.get("params")
    if params is not None and not isinstance(params, (dict, list)):
        raise JsonRpcInvalidRequest("'params' must be an object or array if present")


def is_notification(data: dict[str, Any]) -> bool:
    """Return True when *data* is a JSON-RPC notification (no ``id`` field)."""
    return "id" not in data


# ---------------------------------------------------------------------------
# Custom exception hierarchy (internal; caught by the HTTP layer)
# ---------------------------------------------------------------------------

class JsonRpcError(Exception):
    """Base class for JSON-RPC errors raised during parsing/validation."""

    def __init__(self, code: int, message: str, data: Any = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data

    def to_response(self, request_id: Any = None) -> dict[str, Any]:
        return error_response(request_id, self.code, self.message, self.data)


class JsonRpcParseError(JsonRpcError):
    def __init__(self, detail: str = "Parse error") -> None:
        super().__init__(PARSE_ERROR, detail)


class JsonRpcInvalidRequest(JsonRpcError):
    def __init__(self, detail: str = "Invalid Request") -> None:
        super().__init__(INVALID_REQUEST, detail)


class JsonRpcMethodNotFound(JsonRpcError):
    def __init__(self, method: str) -> None:
        super().__init__(METHOD_NOT_FOUND, f"Method not found: {method}")


class JsonRpcInvalidParams(JsonRpcError):
    def __init__(self, detail: str = "Invalid params") -> None:
        super().__init__(INVALID_PARAMS, detail)


class JsonRpcInternalError(JsonRpcError):
    def __init__(self, detail: str = "Internal error") -> None:
        super().__init__(INTERNAL_ERROR, detail)
