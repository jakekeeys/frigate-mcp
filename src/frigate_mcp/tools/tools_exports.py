"""Export tools for Frigate."""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field


def register_export_tools(mcp: Any, client: Any) -> None:
    """Register Frigate export tools."""

    @mcp.tool()
    async def get_exports() -> dict[str, Any]:
        """List all video exports."""
        exports = await client.get_exports()
        return {"success": True, "count": len(exports), "exports": exports}

    @mcp.tool()
    async def get_export(
        export_id: Annotated[str, Field(description="Export ID")],
    ) -> dict[str, Any]:
        """Get details for a specific export."""
        export = await client.get_export(export_id)
        return {"success": True, "export": export}

    @mcp.tool()
    async def create_export(
        camera: Annotated[str, Field(description="Camera name")],
        start: Annotated[float, Field(description="Start Unix timestamp")],
        end: Annotated[float, Field(description="End Unix timestamp")],
        name: Annotated[str | None, Field(default=None, description="Optional name for the export")] = None,
    ) -> dict[str, Any]:
        """Create a new video export from recorded footage.

        Exports a section of recorded video between the start and end
        timestamps for the specified camera.
        """
        result = await client.create_export(camera, start, end, name=name)
        return {"success": True, "result": result}

    @mcp.tool()
    async def delete_export(
        export_id: Annotated[str, Field(description="Export ID to delete")],
    ) -> dict[str, Any]:
        """Delete a video export."""
        result = await client.delete_export(export_id)
        return {"success": True, "result": result}

    @mcp.tool()
    async def rename_export(
        export_id: Annotated[str, Field(description="Export ID")],
        name: Annotated[str, Field(description="New name for the export")],
    ) -> dict[str, Any]:
        """Rename a video export."""
        result = await client.rename_export(export_id, name)
        return {"success": True, "result": result}
