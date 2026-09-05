# Deployment Guide — Google Cloud Run

This document explains how to deploy the **Construction Reference MCP Remote Server** to Google Cloud Run.

## Prerequisites

- A Google Cloud project with billing enabled.
- [Google Cloud CLI (`gcloud`)](https://cloud.google.com/sdk/docs/install) installed and authenticated.
- Docker installed locally (for optional local testing before deployment).

## 1. Enable Required APIs

```bash
gcloud services enable \
  cloudbuild.googleapis.com \
  run.googleapis.com \
  containerregistry.googleapis.com
```

## 2. Manual Deployment with `gcloud`

### 2.1 Build and push the container

```bash
# From the repository root:
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/construction-reference-mcp
```

### 2.2 Deploy to Cloud Run

```bash
gcloud run deploy construction-reference-mcp \
  --image gcr.io/YOUR_PROJECT_ID/construction-reference-mcp \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --port 8080
```

### 2.3 Find the service URL

After deployment, `gcloud` prints the service URL:

```text
Service URL: https://construction-reference-mcp-XXXXXXXXXX-uc.a.run.app
```

You can also retrieve it with:

```bash
gcloud run services describe construction-reference-mcp \
  --region us-central1 \
  --format "value(status.url)"
```

## 3. Continuous Deployment from GitHub

### 3.1 Connect the repository

1. Go to **Cloud Build → Triggers** in the Google Cloud Console.
2. Click **Connect Repository** and follow the GitHub authorization flow.
3. Select this repository.

### 3.2 Create a build trigger

1. Click **Create Trigger**.
2. Set **Event** to "Push to a branch" and select `main`.
3. Set **Build Configuration** to "Cloud Build configuration file" and specify `cloudbuild.yaml`.
4. Click **Create**.

Every push to `main` will now automatically build and deploy.

### 3.3 `cloudbuild.yaml`

The included `cloudbuild.yaml` performs three steps:

1. Build the Docker image.
2. Push it to Container Registry.
3. Deploy it to Cloud Run.

Default substitutions:
- `_SERVICE_NAME`: `construction-reference-mcp`
- `_REGION`: `us-central1`

Override them via trigger settings or `--substitution` flags.

## 4. Environment Variables

| Variable | Description             | Default |
|----------|-------------------------|---------|
| `PORT`   | HTTP listen port        | `8080`  |
| `HOST`   | HTTP bind address       | `0.0.0.0` |

Cloud Run sets `PORT` automatically. No secrets or API keys are required.

## 5. Configure the MCP Host

In the `mcp-construction-host` configuration, set the remote server URL to:

```text
https://construction-reference-mcp-XXXXXXXXXX-uc.a.run.app/mcp
```

The MCP endpoint is always at `/mcp`.

## 6. Inspect Cloud Run Logs

```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=construction-reference-mcp" \
  --limit 50 \
  --format "table(timestamp, textPayload)"
```

Or use the **Cloud Run → Logs** tab in the Google Cloud Console.

## 7. Delete Resources

To avoid unnecessary charges after the project is complete:

```bash
# Delete the Cloud Run service
gcloud run services delete construction-reference-mcp --region us-central1

# Delete container images
gcloud container images delete gcr.io/YOUR_PROJECT_ID/construction-reference-mcp --force-delete-tags

# (Optional) Disable APIs
gcloud services disable run.googleapis.com cloudbuild.googleapis.com containerregistry.googleapis.com
```

## 8. Wireshark Analysis Notes

### Expected Request Sequence

When the MCP host connects to this remote server, the following network sequence occurs:

1. **TCP connection** — Three-way handshake (SYN → SYN-ACK → ACK).
2. **TLS handshake** — Client Hello, Server Hello, certificate exchange, key exchange (Cloud Run enforces HTTPS).
3. **HTTP POST** to `/mcp` — The JSON-RPC message is in the HTTP body.
4. **JSON-RPC `initialize`** — Client sends the initialize request.
5. **`notifications/initialized`** — Client confirms initialization.
6. **`tools/list`** — Client discovers available tools.
7. **`tools/call`** — Client invokes `get_material_reference`.
8. **JSON-RPC responses** — Server returns results for each request.

### Encryption Note

Public Cloud Run traffic uses HTTPS (TLS 1.2 or 1.3), so the JSON-RPC content inside the TLS tunnel is **encrypted** in Wireshark captures.

To correlate packets:
- Match packet timestamps with the host's JSON-RPC interaction log.
- Identify TCP streams by destination IP (Cloud Run's IP) and port 443.
- Each HTTP request/response pair appears as application data records within the TLS session.

### Local TLS Decryption (Development Only)

For raw JSON-RPC inspection in Wireshark during **local development only**:
- Run the server locally on plain HTTP (default behavior — no TLS locally).
- Use Wireshark to capture on the loopback interface filtering by the server port (e.g., `tcp.port == 8080`).
- The JSON-RPC messages will be visible in cleartext as HTTP POST bodies.

> **Warning**: TLS decryption should only be done in a controlled development environment. Never decrypt production traffic.
