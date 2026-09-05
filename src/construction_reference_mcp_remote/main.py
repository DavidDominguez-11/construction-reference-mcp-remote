"""Application entry point — starts the uvicorn HTTP server."""

from __future__ import annotations

import logging
import sys

import uvicorn

from construction_reference_mcp_remote.config import HOST, PORT

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)

logger = logging.getLogger(__name__)


def main() -> None:
    """Run the MCP server."""
    logger.info("Starting Construction Reference MCP Remote Server on %s:%d", HOST, PORT)
    uvicorn.run(
        "construction_reference_mcp_remote.protocol.http_server:app",
        host=HOST,
        port=PORT,
        log_level="info",
    )


if __name__ == "__main__":
    main()
