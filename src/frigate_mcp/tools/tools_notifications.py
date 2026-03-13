"""Notification tools for Frigate."""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field


def register_notification_tools(mcp: Any, client: Any) -> None:
    """Register Frigate notification tools."""

    @mcp.tool()
    async def get_notifications(
        limit: Annotated[int | None, Field(default=None, description="Max notifications to return")] = None,
        offset: Annotated[int | None, Field(default=None, description="Offset for pagination")] = None,
    ) -> dict[str, Any]:
        """Get Frigate notifications.

        Returns a list of notifications about detected events.
        """
        notifications = await client.get_notifications(
            limit=limit, offset=offset
        )
        return {
            "success": True,
            "count": len(notifications),
            "notifications": notifications,
        }

    @mcp.tool()
    async def mark_notifications_read(
        notification_ids: Annotated[list[str], Field(description="List of notification IDs to mark as read")],
    ) -> dict[str, Any]:
        """Mark notifications as read."""
        result = await client.mark_notifications_read(notification_ids)
        return {"success": True, "result": result}
