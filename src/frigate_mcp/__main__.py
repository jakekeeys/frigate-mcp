"""CLI entry points for frigate-mcp."""

from __future__ import annotations

import logging

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)


def main() -> None:
    """Run the Frigate MCP server (SSE by default, override with MCP_TRANSPORT env)."""
    import os

    from frigate_mcp.server import FrigateMCPServer

    from typing import cast, Literal

    transport = cast(Literal["stdio", "sse", "http", "streamable-http"], os.environ.get("MCP_TRANSPORT", "sse"))
    server = FrigateMCPServer()
    server.mcp.run(transport=transport, host="0.0.0.0", port=8099)


if __name__ == "__main__":
    main()
