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
    async def get_stats_history(
        keys: Annotated[str | None, Field(default=None, description="Comma-separated stat keys to filter (omit for all)")] = None,
    ) -> dict[str, Any]:
        """Get historical stats samples (recent CPU/memory/FPS history)."""
        history = await client.get_stats_history(keys=keys)
        return {"success": True, "history": history}

    @mcp.tool()
    async def get_config() -> dict[str, Any]:
        """Get the full Frigate configuration.

        Returns the complete running config including cameras, detectors,
        objects, recording settings, snapshots, and more.
        """
        config = await client.get_config()
        return {"success": True, "config": config}

    @mcp.tool()
    async def get_config_schema() -> dict[str, Any]:
        """Get the JSON Schema for Frigate's configuration."""
        schema = await client.get_config_schema()
        return {"success": True, "schema": schema}

    @mcp.tool()
    async def save_config(
        config_yaml: Annotated[str, Field(description="Full YAML config text to save")],
        save_option: Annotated[str, Field(default="saveonly", description="'saveonly' to save without restart, 'restart' to save and restart Frigate")] = "saveonly",
    ) -> dict[str, Any]:
        """Save (and optionally restart with) a new Frigate YAML config.

        Admin only. Frigate validates the YAML before persisting it.
        """
        result = await client.save_config(config_yaml, save_option=save_option)
        return {"success": True, "result": result}

    @mcp.tool()
    async def get_plus_models(
        filter_by_current_model_detector: Annotated[bool, Field(default=False, description="Only return models compatible with the active detector")] = False,
    ) -> dict[str, Any]:
        """List available Frigate+ models.

        Requires a configured Frigate+ API key.
        """
        models = await client.get_plus_models(
            filter_by_current_model_detector=filter_by_current_model_detector
        )
        return {"success": True, "models": models}

    @mcp.tool()
    async def get_logs(
        service: Annotated[
            str,
            Field(
                default="frigate",
                description="Log service to retrieve: 'frigate', 'go2rtc', or 'nginx'",
            ),
        ] = "frigate",
        start: Annotated[int | None, Field(default=None, description="First line offset (default 0)")] = None,
        end: Annotated[int | None, Field(default=None, description="Last line offset (default: end of log)")] = None,
    ) -> dict[str, Any]:
        """Get log lines from a Frigate service.

        Returns total_lines plus the requested slice of lines. Frigate logs can
        be large — pass start/end to page through them.
        """
        logs = await client.get_logs(service, start=start, end=end)
        return {
            "success": True,
            "service": service,
            "total_lines": logs.get("totalLines"),
            "lines": logs.get("lines", []),
        }

    @mcp.tool()
    async def restart_frigate() -> dict[str, Any]:
        """Restart the Frigate process.

        WARNING: This will briefly interrupt recording and detection.
        """
        result = await client.restart()
        return {"success": True, "result": result}

    @mcp.tool()
    async def get_config_raw() -> dict[str, Any]:
        """Get the raw Frigate config file as YAML text (as written on disk, not the resolved config)."""
        raw = await client.get_config_raw()
        return {"success": True, "config_yaml": raw}

    @mcp.tool()
    async def set_config(
        config_data: Annotated[dict[str, Any], Field(description="Nested partial config to merge, e.g. {'cameras': {'front': {'detect': {'enabled': False}}}}")],
        requires_restart: Annotated[bool, Field(default=True, description="False applies the change live where Frigate supports it")] = True,
    ) -> dict[str, Any]:
        """Merge a partial update into the Frigate config file.

        Admin only. Frigate validates the result and rolls back on error.
        Prefer this over save_config for small changes.
        """
        result = await client.set_config(config_data, requires_restart=requires_restart)
        return {"success": True, "result": result}

    @mcp.tool()
    async def get_profiles() -> dict[str, Any]:
        """0.18+: List configured profiles (named config overrides) and which is active."""
        result = await client.get_profiles()
        return {"success": True, "profiles": result}

    @mcp.tool()
    async def get_active_profile() -> dict[str, Any]:
        """0.18+: Get the active profile name (null if none). Switch with set_camera_feature(camera='*', feature='profile')."""
        result = await client.get_active_profile()
        return {"success": True, "result": result}
