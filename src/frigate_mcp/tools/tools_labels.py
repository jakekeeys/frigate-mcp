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
    async def get_sub_labels() -> dict[str, Any]:
        """Get all sub-labels (e.g. identified person names, license plates)."""
        sub_labels = await client.get_sub_labels()
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
