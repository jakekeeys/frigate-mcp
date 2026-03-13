"""Frigate MCP Server - core server class."""

from __future__ import annotations

import logging
from typing import Any

from fastmcp import FastMCP

from frigate_mcp import __version__
from frigate_mcp.client.rest_client import FrigateClient
from frigate_mcp.config import get_settings

logger = logging.getLogger(__name__)

SERVER_INSTRUCTIONS = """
You are connected to a Frigate NVR instance via the Frigate MCP Server.

Frigate is an open-source NVR (Network Video Recorder) with real-time AI
object detection for IP cameras.  You can use the tools provided to:

- Query system status, configuration and statistics
- Search and browse detected events (people, cars, animals, etc.)
- View camera snapshots and event thumbnails
- Manage the review queue (mark items as reviewed)
- Manage video exports
- Control PTZ cameras
- Manage recognised faces and license plates
- View recordings and motion activity

Always prefer searching events by semantic description when the user asks
about what happened ("was there a delivery?", "did anyone come to the door?").
Use get_events with label/camera/zone filters for structured queries.
"""


class FrigateMCPServer:
    """Frigate MCP Server wrapping the Frigate HTTP API."""

    def __init__(self) -> None:
        settings = get_settings()
        self.mcp = FastMCP(
            name="frigate-mcp",
            version=__version__,
            instructions=SERVER_INSTRUCTIONS,
        )
        self._client: FrigateClient | None = None
        self._register_tools()
        logger.info("Frigate MCP server initialised (target: %s)", settings.frigate_url)

    @property
    def client(self) -> FrigateClient:
        if self._client is None:
            self._client = FrigateClient()
        return self._client

    def _register_tools(self) -> None:
        """Register all tool modules."""
        from frigate_mcp.tools.tools_system import register_system_tools
        from frigate_mcp.tools.tools_events import register_event_tools
        from frigate_mcp.tools.tools_cameras import register_camera_tools
        from frigate_mcp.tools.tools_recordings import register_recording_tools
        from frigate_mcp.tools.tools_review import register_review_tools
        from frigate_mcp.tools.tools_exports import register_export_tools
        from frigate_mcp.tools.tools_notifications import register_notification_tools
        from frigate_mcp.tools.tools_labels import register_label_tools
        from frigate_mcp.tools.tools_classification import register_classification_tools

        register_system_tools(self.mcp, self.client)
        register_event_tools(self.mcp, self.client)
        register_camera_tools(self.mcp, self.client)
        register_recording_tools(self.mcp, self.client)
        register_review_tools(self.mcp, self.client)
        register_export_tools(self.mcp, self.client)
        register_notification_tools(self.mcp, self.client)
        register_label_tools(self.mcp, self.client)
        register_classification_tools(self.mcp, self.client)
