"""Entry points for the Frigate MCP Server.

Provides ``main()`` (stdio) and ``main_web()`` (streamable-http) transport modes.
"""

from __future__ import annotations

import asyncio
import logging
import signal
import sys

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )


async def _run_stdio() -> None:
    """Run the MCP server over stdio (for Claude Desktop, Claude Code, etc.)."""
    from frigate_mcp.server import create_server

    mcp, client = create_server()
    try:
        await mcp.run_async(transport="stdio")
    finally:
        await client.close()


async def _run_web() -> None:
    """Run the MCP server over streamable HTTP."""
    from frigate_mcp.config import get_settings
    from frigate_mcp.server import create_server

    settings = get_settings()
    mcp, client = create_server()
    try:
        await mcp.run_async(
            transport="streamable-http",
            host=settings.host,
            port=settings.port,
        )
    finally:
        await client.close()


def main() -> None:
    """stdio transport entry point (default for Claude Desktop / Claude Code)."""
    _setup_logging()
    logger.info("Starting Frigate MCP Server (stdio)")
    asyncio.run(_run_stdio())


def main_web() -> None:
    """Streamable HTTP transport entry point."""
    _setup_logging()
    from frigate_mcp.config import get_settings

    settings = get_settings()
    logger.info(
        "Starting Frigate MCP Server (streamable-http) on %s:%s",
        settings.host,
        settings.port,
    )
    asyncio.run(_run_web())


if __name__ == "__main__":
    main()
