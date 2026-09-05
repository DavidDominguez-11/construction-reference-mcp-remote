"""Server configuration loaded from environment variables with safe defaults."""

from __future__ import annotations

import os


# HTTP port — Cloud Run sets PORT; fall back to 8080 for local development.
PORT: int = int(os.getenv("PORT", "8080"))

# Bind address — must be 0.0.0.0 for Docker / Cloud Run.
HOST: str = os.getenv("HOST", "0.0.0.0")

# MCP server identity returned during the initialize handshake.
SERVER_NAME: str = "construction-reference-mcp-remote"
SERVER_VERSION: str = "0.1.0"

# Default location for material lookups.
DEFAULT_LOCATION: str = "Guatemala"
DEFAULT_CURRENCY: str = "GTQ"
