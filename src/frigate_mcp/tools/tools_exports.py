"""Export tools for Frigate."""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field


def register_export_tools(mcp: Any, client: Any) -> None:
    """Register Frigate export tools."""

    @mcp.tool()
    async def get_exports(
        export_case_id: Annotated[str | None, Field(default=None, description="0.18+: only exports in this case")] = None,
        cameras: Annotated[str | None, Field(default=None, description="0.18+: comma-separated camera names")] = None,
        start_date: Annotated[float | None, Field(default=None, description="0.18+: only exports starting after this Unix timestamp")] = None,
        end_date: Annotated[float | None, Field(default=None, description="0.18+: only exports ending before this Unix timestamp")] = None,
    ) -> dict[str, Any]:
        """List video exports. Filters are honoured on Frigate 0.18+ and ignored on 0.17."""
        exports = await client.get_exports(
            export_case_id=export_case_id, cameras=cameras, start_date=start_date, end_date=end_date
        )
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
        name: Annotated[str | None, Field(default=None, description="Optional friendly name for the export")] = None,
        playback: Annotated[str | None, Field(default=None, description="Playback factor: 'realtime' (default), 'timelapse_25x', etc.")] = None,
        source: Annotated[str | None, Field(default=None, description="Source: 'recordings' (default) or 'preview'")] = None,
        chapters: Annotated[str | None, Field(default=None, description="Chapter track mode to embed (see Frigate docs); omit for none")] = None,
        export_case_id: Annotated[str | None, Field(default=None, description="0.18+: assign the export to this case")] = None,
    ) -> dict[str, Any]:
        """Create a new video export from recorded footage.

        Exports a section of recorded video between the start and end
        timestamps for the specified camera. On Frigate 0.18+ `playback` is
        ignored; use create_custom_export for timelapses.
        """
        result = await client.create_export(
            camera, start, end, name=name, playback=playback, source=source,
            chapters=chapters, export_case_id=export_case_id,
        )
        return {"success": True, "result": result}

    @mcp.tool()
    async def delete_export(
        export_id: Annotated[str, Field(description="Export ID to delete")],
    ) -> dict[str, Any]:
        """Delete a video export (routes to the bulk endpoint on Frigate 0.18+)."""
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

    # ------------------------------------------------------------------ #
    # Frigate 0.18+
    # ------------------------------------------------------------------ #

    @mcp.tool()
    async def delete_exports(
        export_ids: Annotated[list[str], Field(description="Export IDs to delete")],
    ) -> dict[str, Any]:
        """0.18+: Bulk delete exports. All IDs must exist and none may be in progress. Admin only."""
        result = await client.delete_exports(export_ids)
        return {"success": True, "result": result}

    @mcp.tool()
    async def reassign_exports(
        export_ids: Annotated[list[str], Field(description="Export IDs to move")],
        export_case_id: Annotated[str | None, Field(default=None, description="Target case ID, or omit to unassign from any case")] = None,
    ) -> dict[str, Any]:
        """0.18+: Move exports into an export case (or out of one)."""
        result = await client.reassign_exports(export_ids, export_case_id)
        return {"success": True, "result": result}

    @mcp.tool()
    async def create_exports_batch(
        items: Annotated[list[dict[str, Any]], Field(description="Up to 50 items, each {camera, start_time, end_time, friendly_name?, image_path?, client_item_id?}")],
        export_case_id: Annotated[str | None, Field(default=None, description="Existing case to attach all exports to (admin only)")] = None,
        new_case_name: Annotated[str | None, Field(default=None, description="Create a new case with this name and attach all exports")] = None,
        new_case_description: Annotated[str | None, Field(default=None, description="Description for the new case")] = None,
    ) -> dict[str, Any]:
        """0.18+: Create several exports (across cameras/time ranges) in one call, optionally grouped into a case."""
        result = await client.create_exports_batch(
            items,
            export_case_id=export_case_id,
            new_case_name=new_case_name,
            new_case_description=new_case_description,
        )
        return {"success": True, "result": result}

    @mcp.tool()
    async def create_custom_export(
        camera: Annotated[str, Field(description="Camera name")],
        start: Annotated[float, Field(description="Start Unix timestamp")],
        end: Annotated[float, Field(description="End Unix timestamp")],
        name: Annotated[str | None, Field(default=None, description="Friendly name")] = None,
        source: Annotated[str | None, Field(default=None, description="'recordings' (default) or 'preview'")] = None,
        ffmpeg_input_args: Annotated[str | None, Field(default=None, description="Custom ffmpeg input args (default: timelapse input args)")] = None,
        ffmpeg_output_args: Annotated[str | None, Field(default=None, description="Custom ffmpeg output args (default: timelapse output args)")] = None,
        cpu_fallback: Annotated[bool | None, Field(default=None, description="Retry without hardware acceleration if the export fails")] = None,
        export_case_id: Annotated[str | None, Field(default=None, description="Assign to this case")] = None,
    ) -> dict[str, Any]:
        """0.18+: Export with custom ffmpeg args. With no args this produces a timelapse (replaces 0.17's playback=timelapse_25x)."""
        result = await client.create_custom_export(
            camera, start, end,
            name=name, source=source,
            ffmpeg_input_args=ffmpeg_input_args, ffmpeg_output_args=ffmpeg_output_args,
            cpu_fallback=cpu_fallback, export_case_id=export_case_id,
        )
        return {"success": True, "result": result}

    @mcp.tool()
    async def get_export_cases() -> dict[str, Any]:
        """0.18+: List export cases (named groups of exports)."""
        cases = await client.get_export_cases()
        return {"success": True, "count": len(cases), "cases": cases}

    @mcp.tool()
    async def get_export_case(
        case_id: Annotated[str, Field(description="Case ID")],
    ) -> dict[str, Any]:
        """0.18+: Get one export case and its exports."""
        case = await client.get_export_case(case_id)
        return {"success": True, "case": case}

    @mcp.tool()
    async def create_export_case(
        name: Annotated[str, Field(description="Case name (max 100 chars)")],
        description: Annotated[str | None, Field(default=None, description="Optional description")] = None,
    ) -> dict[str, Any]:
        """0.18+: Create an export case."""
        result = await client.create_export_case(name, description=description)
        return {"success": True, "result": result}

    @mcp.tool()
    async def update_export_case(
        case_id: Annotated[str, Field(description="Case ID")],
        name: Annotated[str | None, Field(default=None, description="New name")] = None,
        description: Annotated[str | None, Field(default=None, description="New description")] = None,
    ) -> dict[str, Any]:
        """0.18+: Rename or re-describe an export case."""
        result = await client.update_export_case(case_id, name=name, description=description)
        return {"success": True, "result": result}

    @mcp.tool()
    async def delete_export_case(
        case_id: Annotated[str, Field(description="Case ID")],
        delete_exports: Annotated[bool, Field(default=False, description="Also delete the exports in the case (default: just unassign them)")] = False,
    ) -> dict[str, Any]:
        """0.18+: Delete an export case, optionally with its exports."""
        result = await client.delete_export_case(case_id, delete_exports=delete_exports)
        return {"success": True, "result": result}
