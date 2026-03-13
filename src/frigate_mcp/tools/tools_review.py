"""Review queue tools for Frigate."""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field


def register_review_tools(mcp: Any, client: Any) -> None:
    """Register Frigate review tools."""

    @mcp.tool()
    async def get_review(
        cameras: Annotated[str | None, Field(default=None, description="Comma-separated camera names")] = None,
        labels: Annotated[str | None, Field(default=None, description="Comma-separated object labels")] = None,
        zones: Annotated[str | None, Field(default=None, description="Comma-separated zone names")] = None,
        reviewed: Annotated[bool | None, Field(default=None, description="Filter by reviewed status")] = None,
        after: Annotated[float | None, Field(default=None, description="Only items after this Unix timestamp")] = None,
        before: Annotated[float | None, Field(default=None, description="Only items before this Unix timestamp")] = None,
        limit: Annotated[int | None, Field(default=None, description="Max items to return")] = None,
        severity: Annotated[str | None, Field(default=None, description="Filter by severity: 'alert' or 'detection'")] = None,
    ) -> dict[str, Any]:
        """Get review items from the Frigate review queue.

        Review items are detection events that should be checked by a human.
        Severity 'alert' items are higher priority than 'detection' items.
        """
        items = await client.get_review(
            cameras=cameras,
            labels=labels,
            zones=zones,
            reviewed=reviewed,
            after=after,
            before=before,
            limit=limit,
            severity=severity,
        )
        return {"success": True, "count": len(items), "review_items": items}

    @mcp.tool()
    async def get_review_summary(
        cameras: Annotated[str | None, Field(default=None, description="Comma-separated camera names")] = None,
        labels: Annotated[str | None, Field(default=None, description="Comma-separated labels")] = None,
        zones: Annotated[str | None, Field(default=None, description="Comma-separated zones")] = None,
        timezone: Annotated[str | None, Field(default=None, description="IANA timezone")] = None,
    ) -> dict[str, Any]:
        """Get a summary of the review queue.

        Returns counts of reviewed and unreviewed items grouped by day.
        """
        summary = await client.get_review_summary(
            cameras=cameras,
            labels=labels,
            zones=zones,
            timezone=timezone,
        )
        return {"success": True, "summary": summary}

    @mcp.tool()
    async def mark_reviewed(
        review_ids: Annotated[list[str], Field(description="List of review item IDs to mark as reviewed")],
    ) -> dict[str, Any]:
        """Mark one or more review items as reviewed."""
        result = await client.mark_reviewed(review_ids)
        return {"success": True, "result": result}

    @mcp.tool()
    async def delete_reviews(
        review_ids: Annotated[list[str], Field(description="List of review item IDs to delete")],
    ) -> dict[str, Any]:
        """Delete review items."""
        result = await client.delete_reviews(review_ids)
        return {"success": True, "result": result}

    @mcp.tool()
    async def get_motion_activity(
        camera: Annotated[str, Field(description="Camera name")],
        after: Annotated[float | None, Field(default=None, description="Start Unix timestamp")] = None,
        before: Annotated[float | None, Field(default=None, description="End Unix timestamp")] = None,
    ) -> dict[str, Any]:
        """Get motion activity data for a camera.

        Returns periods of motion activity, useful for understanding
        when activity occurred on a camera.
        """
        activity = await client.get_motion_activity(
            camera, after=after, before=before
        )
        return {"success": True, "camera": camera, "activity": activity}
