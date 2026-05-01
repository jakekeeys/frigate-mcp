"""Review queue tools for Frigate."""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field


def register_review_tools(mcp: Any, client: Any) -> None:
    """Register Frigate review tools."""

    @mcp.tool()
    async def get_review(
        cameras: Annotated[str | None, Field(default=None, description="Comma-separated camera names (or 'all')")] = None,
        labels: Annotated[str | None, Field(default=None, description="Comma-separated object labels (or 'all')")] = None,
        zones: Annotated[str | None, Field(default=None, description="Comma-separated zone names (or 'all')")] = None,
        reviewed: Annotated[int | None, Field(default=None, description="0 = only unreviewed, 1 = only reviewed, omit for all")] = None,
        after: Annotated[float | None, Field(default=None, description="Only items after this Unix timestamp (default: 24h ago)")] = None,
        before: Annotated[float | None, Field(default=None, description="Only items before this Unix timestamp (default: now)")] = None,
        limit: Annotated[int | None, Field(default=None, description="Max items to return")] = None,
        severity: Annotated[str | None, Field(default=None, description="Filter by severity: 'alert' or 'detection'")] = None,
    ) -> dict[str, Any]:
        """Get review items from the Frigate review queue.

        Review items are detection segments that should be checked by a human.
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
    async def get_review_by_id(
        review_id: Annotated[str, Field(description="Review segment ID")],
    ) -> dict[str, Any]:
        """Fetch a single review segment by its ID."""
        item = await client.get_review_by_id(review_id)
        return {"success": True, "review": item}

    @mcp.tool()
    async def get_review_by_event(
        event_id: Annotated[str, Field(description="Event ID")],
    ) -> dict[str, Any]:
        """Find the review segment associated with a given event."""
        item = await client.get_review_by_event(event_id)
        return {"success": True, "review": item}

    @mcp.tool()
    async def get_reviews_by_ids(
        review_ids: Annotated[list[str], Field(description="List of review segment IDs to fetch")],
    ) -> dict[str, Any]:
        """Bulk fetch review segments by ID."""
        items = await client.get_reviews_by_ids(review_ids)
        return {"success": True, "count": len(items), "review_items": items}

    @mcp.tool()
    async def get_review_summary(
        cameras: Annotated[str | None, Field(default=None, description="Comma-separated camera names")] = None,
        labels: Annotated[str | None, Field(default=None, description="Comma-separated labels")] = None,
        zones: Annotated[str | None, Field(default=None, description="Comma-separated zones")] = None,
        timezone: Annotated[str | None, Field(default=None, description="IANA timezone")] = None,
    ) -> dict[str, Any]:
        """Get a 24-hour summary of the review queue grouped by severity and day."""
        summary = await client.get_review_summary(
            cameras=cameras,
            labels=labels,
            zones=zones,
            timezone=timezone,
        )
        return {"success": True, "summary": summary}

    @mcp.tool()
    async def mark_reviewed(
        review_ids: Annotated[list[str], Field(description="List of review item IDs")],
        reviewed: Annotated[bool, Field(default=True, description="True to mark as reviewed, False to mark as unreviewed")] = True,
    ) -> dict[str, Any]:
        """Mark review items as reviewed (or unreviewed)."""
        result = await client.mark_reviewed(review_ids, reviewed=reviewed)
        return {"success": True, "result": result}

    @mcp.tool()
    async def unmark_review_viewed(
        review_id: Annotated[str, Field(description="Review item ID to mark as not viewed for the current user")],
    ) -> dict[str, Any]:
        """Mark a single review item as not-viewed for the current user."""
        result = await client.unmark_review_viewed(review_id)
        return {"success": True, "result": result}

    @mcp.tool()
    async def delete_reviews(
        review_ids: Annotated[list[str], Field(description="List of review item IDs to delete")],
    ) -> dict[str, Any]:
        """Delete review items and their associated recordings."""
        result = await client.delete_reviews(review_ids)
        return {"success": True, "result": result}

    @mcp.tool()
    async def get_motion_activity(
        cameras: Annotated[str | None, Field(default=None, description="Comma-separated camera names (or 'all')")] = None,
        after: Annotated[float | None, Field(default=None, description="Start Unix timestamp")] = None,
        before: Annotated[float | None, Field(default=None, description="End Unix timestamp")] = None,
        scale: Annotated[int | None, Field(default=None, description="Scale (seconds per bucket) — controls resolution")] = None,
    ) -> dict[str, Any]:
        """Get motion + audio activity data across cameras and a time range."""
        activity = await client.get_motion_activity(
            cameras=cameras, after=after, before=before, scale=scale
        )
        return {"success": True, "activity": activity}

    @mcp.tool()
    async def summarize_reviews(
        start_ts: Annotated[float, Field(description="Start Unix timestamp")],
        end_ts: Annotated[float, Field(description="End Unix timestamp")],
    ) -> dict[str, Any]:
        """Use Frigate's GenAI provider to summarize review items in a time range.

        Requires GenAI to be configured in Frigate.
        """
        result = await client.summarize_reviews(start_ts, end_ts)
        return {"success": True, "result": result}
