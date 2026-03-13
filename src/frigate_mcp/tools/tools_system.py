"""System / config tools for Frigate."""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field


def register_system_tools(mcp: Any, client: Any) -> None:
    """Register Frigate system tools."""

    @mcp.tool()
    async def get_version() -> dict[str, Any]:
        """Get the Frigate server version string."""
        version = await client.get_version()
        return {"success": True, "version": version}

    @mcp.tool()
    async def get_stats() -> dict[str, Any]:
        """Get Frigate system statistics.

        Returns CPU/memory usage, detector inference speed, camera FPS,
        and per-process resource consumption.
        """
        stats = await client.get_stats()
        return {"success": True, "stats": stats}

    @mcp.tool()
    async def get_config() -> dict[str, Any]:
        """Get the full Frigate configuration.

        Returns the complete running config including cameras, detectors,
        objects, recording settings, snapshots, and more.
        """
        config = await client.get_config()
        return {"success": True, "config": config}

    @mcp.tool()
    async def get_logs(
        service: Annotated[
            str,
            Field(
                default="frigate",
                description="Log service to retrieve: 'frigate', 'go2rtc', or 'nginx'",
            ),
        ] = "frigate",
    ) -> dict[str, Any]:
        """Get recent log output from a Frigate service."""
        logs = await client.get_logs(service)
        return {"success": True, "service": service, "logs": logs}

    @mcp.tool()
    async def restart_frigate() -> dict[str, Any]:
        """Restart the Frigate process.

        WARNING: This will briefly interrupt recording and detection.
        """
        result = await client.restart()
        return {"success": True, "result": result}
