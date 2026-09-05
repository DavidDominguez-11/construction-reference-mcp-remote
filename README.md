# Construction Reference MCP Remote Server

A remote **Model Context Protocol (MCP)** server that provides reference information about construction materials for small projects (houses, offices, commercial spaces) in Guatemala.

Built for the **CC3067 Redes** course project at Universidad del Valle de Guatemala.

> **Disclaimer:** All material prices are **illustrative reference values only**. Actual prices vary by supplier, quality, location, date, quantity, and delivery conditions. This is not financial, professional, or legal advice.

## Features

- Manual **JSON-RPC 2.0** implementation (no MCP SDK).
- **MCP lifecycle**: `initialize`, `notifications/initialized`, `tools/list`, `tools/call`.
- **`get_material_reference`** tool — looks up construction materials by name or alias.
- 11 pre-loaded materials with price ranges in GTQ.
- FastAPI used **only** for HTTP routing (`POST /mcp`, `GET /health`).
- Docker-ready with Google Cloud Run deployment configuration.

## Prerequisites

- Python 3.12+
- pip
- Docker (optional, for container builds)
- Google Cloud CLI (optional, for deployment)

## Installation

```bash
# Clone the repository
git clone https://github.com/YOUR_USER/construction-reference-mcp-remote.git
cd construction-reference-mcp-remote

# Create virtual environment
py -3.12 -m venv .venv

# Activate (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# Activate (Linux/macOS)
# source .venv/bin/activate

# Install with dev dependencies
pip install -e ".[dev]"
```

## Local Execution

```bash
python -m construction_reference_mcp_remote.main
```

The server starts on `http://0.0.0.0:8080` by default. Override with environment variables:

```bash
PORT=9000 python -m construction_reference_mcp_remote.main
```

## Local HTTP Test Examples

### Health check

```bash
curl http://localhost:8080/health
# {"status":"ok"}
```

### Initialize

```bash
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "initialize",
    "id": 1,
    "params": {
      "protocolVersion": "2025-06-18",
      "capabilities": {},
      "clientInfo": {"name": "test-client", "version": "0.1.0"}
    }
  }'
```

### List tools

```bash
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":2}'
```

### Call a tool

```bash
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "id": 3,
    "params": {
      "name": "get_material_reference",
      "arguments": {"material_name": "cement"}
    }
  }'
```

### Unknown material (error case)

```bash
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "id": 4,
    "params": {
      "name": "get_material_reference",
      "arguments": {"material_name": "unobtainium"}
    }
  }'
```

## Docker

### Build

```bash
docker build -t construction-reference-mcp .
```

### Run

```bash
docker run -p 8080:8080 construction-reference-mcp
```

Then test with `curl http://localhost:8080/health`.

## Cloud Run Deployment

See [docs/deployment.md](docs/deployment.md) for complete instructions covering:

- Required Google Cloud APIs
- Manual deployment with `gcloud`
- Continuous deployment from GitHub
- Environment variables
- Finding the service URL
- Configuring the MCP host
- Inspecting logs
- Deleting resources

### Quick Deploy

```bash
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/construction-reference-mcp
gcloud run deploy construction-reference-mcp \
  --image gcr.io/YOUR_PROJECT_ID/construction-reference-mcp \
  --region us-central1 --platform managed --allow-unauthenticated --port 8080
```

## MCP Endpoint

The MCP endpoint is:

```
POST https://<cloud-run-url>/mcp
```

Or locally:

```
POST http://localhost:8080/mcp
```

All requests must use `Content-Type: application/json` and contain valid JSON-RPC 2.0 messages.

## Tool Specification

### `get_material_reference`

Returns reference information for a construction material.

**Parameters:**

| Parameter       | Type   | Required | Description                                       |
|-----------------|--------|----------|---------------------------------------------------|
| `material_name` | string | Yes      | Name or alias of the material                     |
| `location`      | string | No       | Location context (default: `"Guatemala"`)          |

**Available materials:** concrete block 10 cm, concrete block 15 cm, cement, sand, gravel, reinforcing steel bar, electrical conduit, electrical cable, PVC pipe, ceramic floor tile, interior paint.

**Aliases** are supported (e.g., `"rebar"` → reinforcing steel bar, `"pintura"` → interior paint).

**Example response:**

```json
{
  "material_name": "concrete block 15 cm",
  "category": "masonry",
  "unit": "unit",
  "reference_price_range": {
    "minimum": 8.0,
    "maximum": 11.0,
    "currency": "GTQ"
  },
  "reference_updated_at": "2026-09-01",
  "location": "Guatemala",
  "observations": [
    "Standard 15 cm concrete block for structural walls.",
    "Verify strength, dimensions, and supplier delivery conditions."
  ],
  "disclaimer": "Reference values only. Actual prices may vary by supplier, quality, location, date, quantity, and delivery conditions."
}
```

**Error response** (unknown material):

```json
{
  "content": [{"type": "text", "text": "Material 'unobtainium' not found..."}],
  "isError": true
}
```

## Testing

```bash
pytest -v
```

Tests cover:
- JSON-RPC parsing and validation
- Invalid JSON and unknown methods
- MCP lifecycle (initialize, tools/list, tools/call)
- Material aliases and case-insensitive lookup
- Price-range data validity
- Missing/invalid parameters
- Unknown material error
- Default location behavior
- HTTP content-type validation
- Health endpoint
- Full HTTP end-to-end interactions

No Docker, Cloud Run, external APIs, or network connection required.

## Wireshark Analysis Notes

When capturing traffic between the MCP host and this remote server:

1. **TCP** — Three-way handshake (SYN, SYN-ACK, ACK).
2. **TLS** — Client Hello, Server Hello, certificate exchange (Cloud Run uses HTTPS).
3. **HTTP POST** `/mcp` — JSON-RPC messages in the body.
4. **JSON-RPC sequence** — `initialize` → `notifications/initialized` → `tools/list` → `tools/call`.

Since Cloud Run uses HTTPS, the JSON-RPC payload is **encrypted** in Wireshark. To see cleartext JSON-RPC, capture locally on the loopback interface (`tcp.port == 8080`).

See [docs/deployment.md](docs/deployment.md) for detailed Wireshark instructions.

## Limitations

- Reference prices are **illustrative** and do not reflect live market data.
- Location parameter is informational only — prices do not change by location.
- No authentication or authorization (suitable for course project scope).
- No SSE/streaming — uses simple HTTP request/response.
- Single-threaded material lookup from a static JSON file.

## Project Structure

```
construction-reference-mcp-remote/
├── src/
│   └── construction_reference_mcp_remote/
│       ├── __init__.py
│       ├── main.py                    # Entry point
│       ├── config.py                  # Configuration
│       ├── protocol/
│       │   ├── errors.py              # JSON-RPC error codes
│       │   ├── jsonrpc.py             # JSON-RPC 2.0 implementation
│       │   ├── mcp_handler.py         # MCP method dispatcher
│       │   └── http_server.py         # FastAPI HTTP layer
│       ├── tools/
│       │   └── material_reference.py  # get_material_reference tool
│       └── data/
│           └── material_references.json
├── tests/
│   ├── test_jsonrpc.py
│   ├── test_material_reference.py
│   ├── test_mcp_handler.py
│   └── test_http_e2e.py
├── docs/
│   ├── guide.md
│   ├── agent-brief.md
│   └── deployment.md
├── Dockerfile
├── .dockerignore
├── cloudbuild.yaml
├── pyproject.toml
├── .env.example
└── README.md
```

## License

MIT