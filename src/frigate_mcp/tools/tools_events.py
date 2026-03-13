"""Event tools for Frigate."""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field


def register_event_tools(mcp: Any, client: Any) -> None:
    """Register Frigate event tools."""

    @mcp.tool()
    async def get_events(
        camera: Annotated[str | None, Field(default=None, description="Filter by camera name")] = None,
        label: Annotated[str | None, Field(default=None, description="Filter by object label (person, car, dog, etc.)")] = None,
        sub_label: Annotated[str | None, Field(default=None, description="Filter by sub-label (e.g. a person's name)")] = None,
        zone: Annotated[str | None, Field(default=None, description="Filter by zone name")] = None,
        after: Annotated[float | None, Field(default=None, description="Only events after this Unix timestamp")] = None,
        before: Annotated[float | None, Field(default=None, description="Only events before this Unix timestamp")] = None,
        has_clip: Annotated[bool | None, Field(default=None, description="Only events with a video clip")] = None,
        has_snapshot: Annotated[bool | None, Field(default=None, description="Only events with a snapshot")] = None,
        in_progress: Annotated[bool | None, Field(default=None, description="Only currently active events")] = None,
        favorites: Annotated[bool | None, Field(default=None, description="Only favorited/retained events")] = None,
        limit: Annotated[int | None, Field(default=None, description="Max number of events to return (default 20)")] = None,
        min_score: Annotated[float | None, Field(default=None, description="Minimum detection score (0-1)")] = None,
        max_score: Annotated[float | None, Field(default=None, description="Maximum detection score (0-1)")] = None,
    ) -> dict[str, Any]:
        """List detected events from Frigate with optional filters.

        Events represent objects detected by Frigate's AI (people, cars,
        animals, packages, etc.).  Use filters to narrow results by camera,
        label, zone, or time range.
        """
        events = await client.get_events(
            camera=camera,
            label=label,
            sub_label=sub_label,
            zone=zone,
            after=after,
            before=before,
            has_clip=has_clip,
            has_snapshot=has_snapshot,
            in_progress=in_progress,
            favorites=favorites,
            limit=limit,
            min_score=min_score,
            max_score=max_score,
        )
        return {"success": True, "count": len(events), "events": events}

    @mcp.tool()
    async def get_event(
        event_id: Annotated[str, Field(description="The event ID to retrieve")],
    ) -> dict[str, Any]:
        """Get full details for a specific event by its ID."""
        event = await client.get_event(event_id)
        return {"success": True, "event": event}

    @mcp.tool()
    async def search_events(
        query: Annotated[str, Field(description="Natural language search query (e.g. 'person at front door', 'red car')")],
        cameras: Annotated[str | None, Field(default=None, description="Comma-separated camera names to search")] = None,
        labels: Annotated[str | None, Field(default=None, description="Comma-separated labels to filter")] = None,
        zones: Annotated[str | None, Field(default=None, description="Comma-separated zone names")] = None,
        after: Annotated[float | None, Field(default=None, description="Only events after this Unix timestamp")] = None,
        before: Annotated[float | None, Field(default=None, description="Only events before this Unix timestamp")] = None,
        limit: Annotated[int | None, Field(default=None, description="Max results to return")] = None,
        search_type: Annotated[str | None, Field(default=None, description="Search type: 'similarity' or 'text'")] = None,
    ) -> dict[str, Any]:
        """Search events using natural language / semantic search.

        This uses Frigate's built-in semantic search to find events matching
        a description.  Great for queries like "delivery person", "dog in yard",
        or "car in driveway at night".

        Requires Frigate+ or a configured search model.
        """
        events = await client.search_events(
            query,
            cameras=cameras,
            labels=labels,
            zones=zones,
            after=after,
            before=before,
            limit=limit,
            search_type=search_type,
        )
        return {"success": True, "count": len(events), "events": events}

    @mcp.tool()
    async def get_event_summary(
        timezone: Annotated[str | None, Field(default=None, description="IANA timezone for grouping (e.g. 'America/New_York')")] = None,
    ) -> dict[str, Any]:
        """Get a summary of events grouped by label, camera, and day.

        Useful for understanding detection patterns over time.
        """
        summary = await client.get_event_summary(timezone=timezone)
        return {"success": True, "summary": summary}

    @mcp.tool()
    async def delete_event(
        event_id: Annotated[str, Field(description="Event ID to delete")],
    ) -> dict[str, Any]:
        """Delete a specific event and its associated media."""
        result = await client.delete_event(event_id)
        return {"success": True, "result": result}

    @mcp.tool()
    async def retain_event(
        event_id: Annotated[str, Field(description="Event ID")],
        retain: Annotated[bool, Field(description="True to retain/favorite, False to un-retain")],
    ) -> dict[str, Any]:
        """Mark an event as retained (favorited) so it won't be auto-deleted."""
        result = await client.retain_event(event_id, retain)
        return {"success": True, "result": result}

    @mcp.tool()
    async def set_event_sub_label(
        event_id: Annotated[str, Field(description="Event ID")],
        sub_label: Annotated[str, Field(description="Sub-label to set (e.g. person's name)")],
    ) -> dict[str, Any]:
        """Set a sub-label on an event (e.g. to identify a specific person)."""
        result = await client.set_sub_label(event_id, sub_label)
        return {"success": True, "result": result}

    @mcp.tool()
    async def set_event_description(
        event_id: Annotated[str, Field(description="Event ID")],
        description: Annotated[str, Field(description="Description text for the event")],
    ) -> dict[str, Any]:
        """Set a text description on an event."""
        result = await client.set_description(event_id, description)
        return {"success": True, "result": result}

    @mcp.tool()
    async def create_event(
        camera: Annotated[str, Field(description="Camera name to create the event on")],
        label: Annotated[str, Field(description="Object label for the event")],
        sub_label: Annotated[str | None, Field(default=None, description="Optional sub-label")] = None,
        duration: Annotated[int | None, Field(default=None, description="Event duration in seconds")] = None,
        include_recording: Annotated[bool | None, Field(default=None, description="Include recording clip")] = None,
    ) -> dict[str, Any]:
        """Manually create an event on a camera.

        Useful for marking a time period as notable even if Frigate didn't
        detect anything automatically.
        """
        result = await client.create_event(
            camera,
            label,
            sub_label=sub_label,
            duration=duration,
            include_recording=include_recording,
        )
        return {"success": True, "result": result}

    @mcp.tool()
    async def end_event(
        event_id: Annotated[str, Field(description="Event ID to end")],
    ) -> dict[str, Any]:
        """End an in-progress event that was manually created."""
        result = await client.end_event(event_id)
        return {"success": True, "result": result}

    @mcp.tool()
    async def mark_event_false_positive(
        event_id: Annotated[str, Field(description="Event ID to mark as false positive")],
    ) -> dict[str, Any]:
        """Mark an event as a false positive detection."""
        result = await client.mark_event_as_false_positive(event_id)
        return {"success": True, "result": result}
