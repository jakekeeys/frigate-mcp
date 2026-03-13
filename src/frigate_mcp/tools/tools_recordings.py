"""Recording tools for Frigate."""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field


def register_recording_tools(mcp: Any, client: Any) -> None:
    """Register Frigate recording tools."""

    @mcp.tool()
    async def get_recording_summary(
        camera: Annotated[str, Field(description="Camera name")],
        timezone: Annotated[str | None, Field(default=None, description="IANA timezone (e.g. 'America/New_York')")] = None,
    ) -> dict[str, Any]:
        """Get a summary of recordings for a camera.

        Returns recording hours grouped by day, useful for understanding
        how much footage is available.
        """
        summary = await client.get_recording_summary(camera, timezone=timezone)
        return {"success": True, "camera": camera, "summary": summary}

    @mcp.tool()
    async def get_recording_storage() -> dict[str, Any]:
        """Get recording storage usage across all cameras.

        Returns disk usage information for the recording storage.
        """
        storage = await client.get_recording_storage()
        return {"success": True, "storage": storage}
