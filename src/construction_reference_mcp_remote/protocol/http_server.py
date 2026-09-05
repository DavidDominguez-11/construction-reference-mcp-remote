"""FastAPI HTTP server — thin transport layer for the MCP JSON-RPC handler.

FastAPI is used **only** for HTTP routing and server execution.
All JSON-RPC 2.0 and MCP logic is implemented manually in `jsonrpc.py`
and `mcp_handler.py`.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from construction_reference_mcp_remote.protocol.jsonrpc import (
    JsonRpcError,
    JsonRpcInternalError,
    parse_request,
    validate_request,
    error_response,
)
from construction_reference_mcp_remote.protocol.mcp_handler import handle_request

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Construction Reference MCP Remote Server",
    version="0.1.0",
    docs_url=None,       # Disable Swagger UI — this is a JSON-RPC endpoint.
    redoc_url=None,
    openapi_url=None,
)


# ---------------------------------------------------------------------------
# Health endpoint (for Cloud Run / load balancer probes)
# ---------------------------------------------------------------------------

@app.get("/health")
async def health() -> dict[str, str]:
    """Simple liveness / readiness probe."""
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# MCP endpoint — POST /mcp
# ---------------------------------------------------------------------------

@app.post("/mcp")
async def mcp_endpoint(request: Request) -> JSONResponse:
    """Receive a JSON-RPC 2.0 request, route it through the MCP handler,
    and return the JSON-RPC response.
    """
    # --- Content-Type validation ---
    content_type = request.headers.get("content-type", "")
    if "application/json" not in content_type:
        return JSONResponse(
            status_code=415,
            content={"error": "Unsupported Media Type. Content-Type must be application/json."},
        )

    # --- Read raw body ---
    raw_body = await request.body()

    # --- Parse JSON ---
    try:
        data = parse_request(raw_body)
    except JsonRpcError as exc:
        return JSONResponse(
            status_code=200,
            content=exc.to_response(),
            media_type="application/json",
        )

    # --- Validate JSON-RPC structure ---
    request_id: Any = data.get("id")
    try:
        validate_request(data)
    except JsonRpcError as exc:
        return JSONResponse(
            status_code=200,
            content=exc.to_response(request_id),
            media_type="application/json",
        )

    # --- Dispatch to MCP handler ---
    try:
        response = handle_request(data)
    except JsonRpcError as exc:
        return JSONResponse(
            status_code=200,
            content=exc.to_response(request_id),
            media_type="application/json",
        )
    except Exception:
        logger.exception("Unhandled exception in MCP handler")
        err = JsonRpcInternalError("An unexpected server error occurred.")
        return JSONResponse(
            status_code=200,
            content=err.to_response(request_id),
            media_type="application/json",
        )

    # Notifications return None — respond with 204 No Content.
    if response is None:
        return Response(status_code=204)

    return JSONResponse(
        status_code=200,
        content=response,
        media_type="application/json",
    )
