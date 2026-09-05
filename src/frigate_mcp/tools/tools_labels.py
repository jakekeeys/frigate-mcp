"""Label and timeline tools for Frigate."""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field


def register_label_tools(mcp: Any, client: Any) -> None:
    """Register Frigate label and timeline tools."""

    @mcp.tool()
    async def get_labels(
        camera: Annotated[str | None, Field(default=None, description="Camera name to filter labels for")] = None,
    ) -> dict[str, Any]:
        """Get all object labels that have been detected.

        Optionally filter to labels seen on a specific camera.
        Common labels: person, car, dog, cat, bird, package, etc.
        """
        labels = await client.get_labels(camera=camera)
        return {"success": True, "labels": labels}

    @mcp.tool()
    async def get_sub_labels(
        split_joined: Annotated[int | None, Field(default=None, description="If 1, split joined sub-labels (e.g. 'Alice,Bob') into separate entries")] = None,
    ) -> dict[str, Any]:
        """Get all sub-labels (e.g. identified person names)."""
        sub_labels = await client.get_sub_labels(split_joined=split_joined)
        return {"success": True, "sub_labels": sub_labels}

    @mcp.tool()
    async def get_timeline(
        camera: Annotated[str | None, Field(default=None, description="Camera name")] = None,
        source_id: Annotated[str | None, Field(default=None, description="Source event ID")] = None,
        limit: Annotated[int | None, Field(default=None, description="Max entries to return")] = None,
    ) -> dict[str, Any]:
        """Get the detection timeline.

        The timeline shows a chronological sequence of detection events
        with their progression (object entered zone, attribute changes, etc.).
        """
        timeline = await client.get_timeline(
            camera=camera, source_id=source_id, limit=limit
        )
        return {"success": True, "count": len(timeline), "timeline": timeline}

    @mcp.tool()
    async def get_timeline_hourly(
        cameras: Annotated[str | None, Field(default=None, description="Comma-separated camera names (or 'all')")] = None,
        labels: Annotated[str | None, Field(default=None, description="Comma-separated labels (or 'all')")] = None,
        before: Annotated[float | None, Field(default=None, description="End Unix timestamp")] = None,
        after: Annotated[float | None, Field(default=None, description="Start Unix timestamp")] = None,
        timezone: Annotated[str | None, Field(default=None, description="IANA timezone")] = None,
    ) -> dict[str, Any]:
        """Get hourly bucketed timeline summary."""
        result = await client.get_timeline_hourly(
            cameras=cameras,
            labels=labels,
            before=before,
            after=after,
            timezone=timezone,
        )
        return {"success": True, "timeline": result}

    @mcp.tool()
    async def get_audio_labels() -> dict[str, Any]:
        """0.18+: Get all audio labels that have been detected (e.g. speech, bark, siren)."""
        labels = await client.get_audio_labels()
        return {"success": True, "audio_labels": labels}
