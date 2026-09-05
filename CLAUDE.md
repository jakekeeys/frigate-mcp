# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A FastMCP server that exposes the [Frigate NVR](https://frigate.video) HTTP API (v0.17.2) as MCP tools. 73 tools across 8 categories let an MCP client query events, view frames, manage exports/review queue, summarise review activity via GenAI, and manage registered faces. PTZ is intentionally **not** included — Frigate's PTZ control surface is MQTT-only, not HTTP.

## Common commands

```bash
# Install for local development
pip install -e .          # or: uv pip install -e .

# Run the server
python -m frigate_mcp     # stdio transport (Claude Desktop / Claude Code)
frigate-mcp               # same, via console script
frigate-mcp-web           # streamable-http transport, binds MCP_HOST:MCP_PORT (default 0.0.0.0:8086)

# Lint
ruff check .
ruff format .

# Container
docker compose up --build # builds and runs frigate-mcp-web on :8086
```

There is no test suite. `FRIGATE_URL` must be set (env var or `.env`) for the server to talk to a real Frigate instance.

## Architecture

The server is a thin async wrapper around Frigate's REST API. Three layers:

1. **`client/rest_client.py`** — `FrigateClient` is an `httpx.AsyncClient` with a single `_request()` helper that centralizes error handling (`FrigateAPIError` for HTTP 4xx/5xx, `FrigateConnectionError` for connect/timeout). All Frigate endpoints have a typed method on this class. `raw=True` returns the raw `httpx.Response` for binary payloads (snapshots, thumbnails). The client lazily creates the underlying httpx client on first use and must be `close()`d on shutdown.

2. **`tools/tools_*.py`** — Each module defines a `register_<category>_tools(mcp, client)` function that registers `@mcp.tool()` async functions. Tools are thin: validate args via `Annotated[..., Field(...)]`, call the client, wrap the result in `{"success": True, ...}`. Image-returning tools (snapshots, frames, thumbnails) base64-encode the bytes.

3. **`server.py`** — `create_server()` builds a `FastMCP` instance, instantiates one `FrigateClient`, and calls each `register_*_tools()` in turn. Returns `(mcp, client)` so the entry point can manage the client's lifecycle. `SERVER_INSTRUCTIONS` is shipped to MCP clients as the server's system prompt.

`__main__.py` provides two entry points: `main()` runs stdio, `main_web()` runs streamable-http. Both `load_dotenv()` at import time and ensure `client.close()` runs in a `finally`.

`config.py` uses `pydantic-settings` with env var aliases (`FRIGATE_URL`, `FRIGATE_TIMEOUT`, `MCP_HOST`, `MCP_PORT`). `get_settings()` is `@lru_cache`d — settings are effectively a singleton.

## Adding a new tool

1. Add the underlying HTTP method on `FrigateClient` in `rest_client.py` (use `_request` — never call `self.client` directly for non-raw responses).
2. Add a `@mcp.tool()` async function in the appropriate `tools/tools_*.py` module. If no module fits, create a new one and register it from `server.py`.
3. Tools should return `dict[str, Any]` with a `success` key. For binary responses, base64-encode and include a `mime_type` field (see `tools_classification.py` for the pattern).

## Conventions

- Python 3.11+, `from __future__ import annotations` everywhere, `str | None` unions over `Optional`.
- Ruff config: line length 88 (E501 ignored), targets `E W F I B UP`.
- README claims "73 tools across 8 categories" — keep this in sync if you add/remove tools.
- Endpoints are **verified against the Frigate v0.17.2 source** (`github.com/blakeblackshear/frigate`, files under `frigate/api/`). When adding a tool, confirm the route exists in that release before writing the client method — avoid modeling endpoints from intuition. License plate CRUD, notifications list/mark-read, and `POST /api/{camera}/ptz` are common traps that look like they should exist but don't. Boolean query flags (`has_clip`, `favorites`, …) are typed `Optional[int]` upstream — pass through `_flag()` in the client, never a raw bool.
- Multipart uploads (face register/recognize, Frigate+ submit) are intentionally not exposed — this client is JSON/binary-read-only.
