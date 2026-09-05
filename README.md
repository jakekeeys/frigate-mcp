# Frigate MCP Server

A [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server for [Frigate NVR](https://frigate.video), built with [FastMCP](https://github.com/jlowin/fastmcp).

Control and query your Frigate NVR instance through AI assistants like Claude Desktop, Claude Code, or any MCP-compatible client using natural language.

## Features

**90 tools** across 8 categories, mapped 1:1 to Frigate's HTTP API. Verified against v0.17.2 and v0.18.0-rc1; tools marked **0.18+** need Frigate 0.18, everything else works on both (the export-delete change is handled automatically):

| Category | Tools | Description |
|----------|-------|-------------|
| **System** | 13 | Version, stats (+history), config (get/raw/set/save/schema), logs, restart, Frigate+ models, profiles (0.18+) |
| **Events** | 21 | List, explore, by-id, search, summary, create/end/delete (single + bulk), retain, false-positive, sub-label, recognized plate, attributes, description, regenerate description, semantic-search trigger status + embedding CRUD |
| **Cameras** | 7 | Latest frame, latest "best" thumbnail per camera + label, PTZ info (read-only), set camera feature (0.18+), VLM monitor start/get/cancel (0.18+) |
| **Recordings** | 7 | Per-camera summary, days with recordings, storage, list segments, recording gaps, frame at timestamp, delete range (0.18+) |
| **Review** | 10 | List, by-id, by-event, by-ids, summary, mark/unmark viewed, delete, motion activity, AI summary |
| **Exports** | 14 | List (filters), get, create, delete, rename, bulk delete/reassign/batch (0.18+), custom ffmpeg export (0.18+), export cases CRUD (0.18+) |
| **Labels** | 5 | Labels, sub-labels, audio labels (0.18+), timeline, hourly timeline |
| **Classification** | 13 | Faces CRUD (folder/delete/rename/reprocess/list), recognized plates, LPR reprocess, event thumbnail/snapshot/clean snapshot/preview GIF, audio transcription, embeddings reindex |

PTZ camera *control* is **not** included — Frigate exposes PTZ over MQTT, not HTTP. Read-only PTZ info is.

## Quick Start

### Prerequisites

- Python 3.11+
- A running [Frigate](https://docs.frigate.video) instance

### Install

```bash
# Clone the repo
git clone https://github.com/jakekeeys/frigate-mcp.git
cd frigate-mcp

# Install with pip
pip install -e .

# Or with uv
uv pip install -e .
```

### Configure

Set the `FRIGATE_URL` environment variable pointing to your Frigate instance:

```bash
export FRIGATE_URL=http://192.168.1.50:5000
```

Or create a `.env` file (see `.env.example`):

```
FRIGATE_URL=http://192.168.1.50:5000
```

### Run

```bash
# Run via module
python -m frigate_mcp

# Or via the installed entry point
frigate-mcp
```

## MCP Client Configuration

### Claude Desktop

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS, `%APPDATA%\Claude\claude_desktop_config.json` on Windows):

```json
{
  "mcpServers": {
    "frigate": {
      "command": "python",
      "args": ["-m", "frigate_mcp"],
      "env": {
        "FRIGATE_URL": "http://your-frigate-ip:5000"
      }
    }
  }
}
```

### Claude Code

```bash
claude mcp add frigate -- python -m frigate_mcp
```

Then set `FRIGATE_URL` in your environment or `.env` file.

### Using uvx (no install needed)

```json
{
  "mcpServers": {
    "frigate": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/jakekeeys/frigate-mcp", "frigate-mcp"],
      "env": {
        "FRIGATE_URL": "http://your-frigate-ip:5000"
      }
    }
  }
}
```

## Example Queries

Once connected, you can ask your AI assistant things like:

- *"What cameras are configured in Frigate?"*
- *"Show me recent person detections"*
- *"Were there any cars in the driveway today?"*
- *"Search for delivery person events"*
- *"Show me the latest frame from the front door camera"*
- *"How much recording storage is being used?"*
- *"Mark all review items from today as reviewed"*
- *"Create an export of the backyard camera from 2pm to 3pm"*
- *"What faces has Frigate learned?"*
- *"Summarise everything that happened in the review queue overnight"*
- *"Show me the system stats"*

## Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `FRIGATE_URL` | `http://localhost:5000` | Frigate instance URL |
| `FRIGATE_TIMEOUT` | `30` | HTTP request timeout (seconds) |

## Architecture

```
src/frigate_mcp/
    __init__.py          # Package version
    __main__.py          # CLI entry point (stdio transport)
    config.py            # Pydantic Settings from env vars
    server.py            # FrigateMCPServer (FastMCP wrapper)
    client/
        rest_client.py   # Async httpx client for Frigate API
    tools/
        tools_system.py         # System/config tools
        tools_events.py         # Event CRUD, search, attributes, description
        tools_cameras.py        # Camera frames + best-per-label thumbnails
        tools_recordings.py     # Recording summary, segments, gaps
        tools_review.py         # Review queue + GenAI summary
        tools_exports.py        # Video exports
        tools_labels.py         # Labels, sub-labels, timeline
        tools_classification.py # Faces + recognised plates + event media
```

## License

MIT
