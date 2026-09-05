"""Recording tools for Frigate."""

from __future__ import annotations

import base64
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

    @mcp.tool()
    async def get_recording_days(
        cameras: Annotated[str | None, Field(default=None, description="Comma-separated camera names (default all)")] = None,
        timezone: Annotated[str | None, Field(default=None, description="IANA timezone")] = None,
    ) -> dict[str, Any]:
        """Get which days have any recordings across cameras (day -> true)."""
        days = await client.get_recording_days(cameras=cameras, timezone=timezone)
        return {"success": True, "days": days}

    @mcp.tool()
    async def get_recording_snapshot(
        camera: Annotated[str, Field(description="Camera name")],
        frame_time: Annotated[float, Field(description="Unix timestamp of the frame to extract")],
        fmt: Annotated[str, Field(default="jpg", description="'jpg' or 'png'")] = "jpg",
        height: Annotated[int | None, Field(default=None, description="Resize to this height in pixels")] = None,
    ) -> dict[str, Any]:
        """Extract a single frame from recorded footage at a timestamp, as base64."""
        image_bytes = await client.get_recording_snapshot(
            camera, frame_time, fmt=fmt, height=height
        )
        return {
            "success": True,
            "camera": camera,
            "frame_time": frame_time,
            "image_base64": base64.b64encode(image_bytes).decode("ascii"),
            "content_type": "image/png" if fmt == "png" else "image/jpeg",
        }

    @mcp.tool()
    async def delete_recordings(
        start: Annotated[float, Field(description="Start Unix timestamp")],
        end: Annotated[float, Field(description="End Unix timestamp (must be after start)")],
        cameras: Annotated[str | None, Field(default=None, description="Comma-separated camera names (default all)")] = None,
        keep: Annotated[str | None, Field(default=None, description="Comma-separated recording IDs to keep within the range")] = None,
    ) -> dict[str, Any]:
        """0.18+: Delete recording segments overlapping a time range. Irreversible."""
        result = await client.delete_recordings(start, end, cameras=cameras, keep=keep)
        return {"success": True, "result": result}
