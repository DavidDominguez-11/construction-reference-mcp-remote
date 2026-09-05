"""MCP request handler — routes JSON-RPC methods to tool implementations.

Implements:
  - initialize
  - notifications/initialized
  - tools/list
  - tools/call
  - Unknown-method errors
"""

from __future__ import annotations

import json
import logging
from typing import Any

from construction_reference_mcp_remote.config import SERVER_NAME, SERVER_VERSION
from construction_reference_mcp_remote.protocol.jsonrpc import (
    JsonRpcInvalidParams,
    JsonRpcInternalError,
    JsonRpcMethodNotFound,
    error_response,
    is_notification,
    success_response,
)
from construction_reference_mcp_remote.tools.material_reference import (
    TOOL_DEFINITION,
    MaterialNotFoundError,
    execute as execute_material_reference,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

# Registry of available tools — easily extensible.
_TOOLS: dict[str, dict[str, Any]] = {
    "get_material_reference": TOOL_DEFINITION,
}


def handle_request(data: dict[str, Any]) -> dict[str, Any] | None:
    """Dispatch a validated JSON-RPC request to the appropriate MCP handler.

    Returns a JSON-RPC response dict, or ``None`` for notifications.
    """
    method: str = data["method"]
    params: dict[str, Any] = data.get("params") or {}
    request_id: Any = data.get("id")

    # --- Notifications (no id → no response) ---
    if is_notification(data):
        return _handle_notification(method, params)

    # --- Requests (must return a response) ---
    handler = _METHOD_DISPATCH.get(method)
    if handler is None:
        raise JsonRpcMethodNotFound(method)

    return handler(request_id, params)


# ---------------------------------------------------------------------------
# Method handlers
# ---------------------------------------------------------------------------

def _handle_initialize(request_id: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Respond to the MCP ``initialize`` handshake."""
    logger.info("MCP initialize request received (id=%s)", request_id)
    return success_response(request_id, {
        "protocolVersion": "2025-06-18",
        "capabilities": {
            "tools": {},
        },
        "serverInfo": {
            "name": SERVER_NAME,
            "version": SERVER_VERSION,
        },
    })


def _handle_tools_list(request_id: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Return the list of available MCP tools."""
    logger.info("tools/list request received (id=%s)", request_id)
    return success_response(request_id, {
        "tools": list(_TOOLS.values()),
    })


def _handle_tools_call(request_id: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Execute an MCP tool by name."""
    tool_name = params.get("name")
    if not tool_name or not isinstance(tool_name, str):
        raise JsonRpcInvalidParams("'name' is required in tools/call params")

    if tool_name not in _TOOLS:
        raise JsonRpcInvalidParams(f"Unknown tool: {tool_name}")

    arguments: dict[str, Any] = params.get("arguments") or {}
    logger.info("tools/call '%s' (id=%s) arguments=%s", tool_name, request_id, arguments)

    try:
        if tool_name == "get_material_reference":
            result = execute_material_reference(arguments)
        else:
            raise JsonRpcInvalidParams(f"Unknown tool: {tool_name}")
    except MaterialNotFoundError as exc:
        # Tool-level error — returned as a valid JSON-RPC result with isError=true.
        return success_response(request_id, {
            "content": [
                {
                    "type": "text",
                    "text": str(exc),
                }
            ],
            "isError": True,
        })
    except ValueError as exc:
        raise JsonRpcInvalidParams(str(exc)) from exc
    except Exception as exc:
        # Catch-all — do not expose stack traces.
        logger.exception("Unexpected error in tools/call '%s'", tool_name)
        raise JsonRpcInternalError("An unexpected error occurred while executing the tool.") from exc

    return success_response(request_id, {
        "content": [
            {
                "type": "text",
                "text": json.dumps(result, ensure_ascii=False),
            }
        ],
    })


def _handle_notification(method: str, params: dict[str, Any]) -> None:
    """Handle JSON-RPC notifications (no response expected)."""
    if method == "notifications/initialized":
        logger.info("MCP client confirmed initialization.")
        return None
    # Unknown notifications are silently ignored per JSON-RPC spec.
    logger.debug("Ignoring unknown notification: %s", method)
    return None


# ---------------------------------------------------------------------------
# Dispatch table
# ---------------------------------------------------------------------------

_METHOD_DISPATCH: dict[str, Any] = {
    "initialize": _handle_initialize,
    "tools/list": _handle_tools_list,
    "tools/call": _handle_tools_call,
}
