"""JSON-RPC 2.0 standard and MCP-specific error codes.

Reference:
  - JSON-RPC 2.0 spec: https://www.jsonrpc.org/specification#error_object
  - MCP spec error codes.
"""

from __future__ import annotations


# --- JSON-RPC 2.0 standard error codes ---

PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603

# --- Human-readable default messages ---

ERROR_MESSAGES: dict[int, str] = {
    PARSE_ERROR: "Parse error",
    INVALID_REQUEST: "Invalid Request",
    METHOD_NOT_FOUND: "Method not found",
    INVALID_PARAMS: "Invalid params",
    INTERNAL_ERROR: "Internal error",
}
