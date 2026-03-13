# Frigate MCP Server

A [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server for [Frigate NVR](https://frigate.video), built with [FastMCP](https://github.com/jlowin/fastmcp).

Control and query your Frigate NVR instance through AI assistants like Claude Desktop, Claude Code, or any MCP-compatible client using natural language.

## Features

**45 tools** across 9 categories:

| Category | Tools | Description |
|----------|-------|-------------|
| **System** | 5 | Config, stats, version, logs, restart |
| **Events** | 12 | List, get, search, create, delete, retain, sub-label, describe, false-positive |
| **Cameras** | 3 | Latest frame, PTZ info, PTZ commands |
| **Recordings** | 2 | Recording summary, storage usage |
| **Review** | 5 | Queue, summary, mark reviewed, delete, motion activity |
| **Exports** | 5 | List, get, create, delete, rename |
| **Notifications** | 2 | List, mark read |
| **Labels** | 3 | Labels, sub-labels, timeline |
| **Classification** | 8 | Faces CRUD, license plates CRUD, thumbnails, snapshots |

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
- *"Register license plate ABC-1234 as 'Mom'"*
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
        tools_events.py         # Event CRUD + search
        tools_cameras.py        # Camera frames + PTZ
        tools_recordings.py     # Recording info
        tools_review.py         # Review queue
        tools_exports.py        # Video exports
        tools_notifications.py  # Notifications
        tools_labels.py         # Labels + timeline
        tools_classification.py # Faces + license plates + media
```

## License

MIT
