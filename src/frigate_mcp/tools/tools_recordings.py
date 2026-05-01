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

    @mcp.tool()
    async def get_recordings(
        camera: Annotated[str, Field(description="Camera name")],
        after: Annotated[float | None, Field(default=None, description="Start Unix timestamp (default: 1h ago)")] = None,
        before: Annotated[float | None, Field(default=None, description="End Unix timestamp (default: now)")] = None,
    ) -> dict[str, Any]:
        """List recording segments for a camera in a time range."""
        recordings = await client.get_recordings(camera, after=after, before=before)
        return {
            "success": True,
            "camera": camera,
            "count": len(recordings),
            "recordings": recordings,
        }

    @mcp.tool()
    async def get_recordings_unavailable(
        cameras: Annotated[str | None, Field(default=None, description="Comma-separated camera names (or 'all')")] = None,
        after: Annotated[float | None, Field(default=None, description="Start Unix timestamp (default: 1h ago)")] = None,
        before: Annotated[float | None, Field(default=None, description="End Unix timestamp (default: now)")] = None,
        scale: Annotated[int | None, Field(default=None, description="Bucket size in seconds")] = None,
    ) -> dict[str, Any]:
        """Get time ranges where no recordings are available (gaps)."""
        gaps = await client.get_recordings_unavailable(
            cameras=cameras, after=after, before=before, scale=scale
        )
        return {"success": True, "gaps": gaps}
