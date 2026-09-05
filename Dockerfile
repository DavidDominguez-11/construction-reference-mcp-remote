# syntax=docker/dockerfile:1
FROM python:3.12-slim AS base

# Prevent Python from writing .pyc files and enable unbuffered output.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Copy all files necessary for installation (metadata and source)
COPY pyproject.toml README.md ./
COPY src/ ./src/

# Install the project.
RUN pip install --no-cache-dir .

# Cloud Run injects PORT; default to 8080 for local testing.
ENV PORT=8080

EXPOSE 8080

CMD ["python", "-m", "construction_reference_mcp_remote.main"]
