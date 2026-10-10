"""System / config tools for Frigate."""

from __future__ import annotations

from typing import Annotated, Any

_MISSING = object()
_SENSITIVE = {"password", "passwd", "secret", "token", "api_key", "private_key", "username", "user", "rtsp", "input_args", "path"}


def _config_field(config: dict[str, Any], field_path: str) -> Any:
    """Read a simple dotted object path, refusing secrets and array indexing."""
    parts = field_path.split(".")
    if not parts or any(not p or p.startswith("_") or p.isdigit() for p in parts):
        raise ValueError("Invalid config field path")
    if any(p.lower() in _SENSITIVE or "password" in p.lower() or "secret" in p.lower() or "token" in p.lower() for p in parts):
        raise ValueError("Sensitive configuration fields are not exposed by this tool")
    node: Any = config
    for part in parts:
        if not isinstance(node, dict) or part not in node:
            raise ValueError(f"Unknown config field: {field_path}")
        node = node[part]
    if isinstance(node, (dict, list)):
        raise ValueError("Select an individual scalar field rather than a section or list")
    return node


def _nested_field(field_path: str, value: Any) -> dict[str, Any]:
    node: Any = value
    for part in reversed(field_path.split(".")):
        node = {part: node}
    return node

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
    async def get_config_field(field_path: str) -> dict[str, Any]:
        """Read one nonsensitive scalar using a dotted path, e.g. genai.model."""
        current = await client.get_config()
        value = _config_field(current, field_path)
        return {"success": True, "field_path": field_path, "value": value}

    @mcp.tool()
    async def update_config_field(
        field_path: str,
        value: Any,
        expected_value: Any,
        dry_run: bool = True,
        requires_restart: bool = True,
    ) -> dict[str, Any]:
        """Safely modify one nonsensitive scalar using Frigate's partial config API.

        expected_value is mandatory and must equal the current resolved value.
        dry_run defaults to True. A successful write may still need Frigate
        restart; the tool does not restart or change other fields.
        For sensitive fields use Frigate's authenticated config editor.
        """
        config = await client.get_config()
        old_value = _config_field(config, field_path)
        if old_value != expected_value or type(old_value) is not type(expected_value):
            return {"success": False, "error": "config_conflict", "field_path": field_path,
                    "message": "The existing value differs from expected_value; no changes made."}
        if isinstance(value, (dict, list)) or value is None:
            raise ValueError("Only non-null scalar values are supported")
        if type(value) is not type(old_value):
            raise ValueError("New value must have the same JSON type as the previous value")
        if value == old_value:
            return {"success": True, "changed": False, "field_path": field_path,
                    "requires_restart": False}
        result = {"success": True, "field_path": field_path, "old_value": old_value,
                  "new_value": value, "dry_run": dry_run, "requires_restart": requires_restart}
        if dry_run:
            return result
        # Frigate performs its own validation and restores the file on validation errors.
        response = await client.set_config(_nested_field(field_path, value),
                                           requires_restart=requires_restart)
        if isinstance(response, dict) and response.get("success") is False:
            return {**result, "success": False, "result": response}
        result["result"] = response
        # When restart is required, the running config remains stale until restart.
        if not requires_restart:
            result["verified_value"] = _config_field(await client.get_config(), field_path)
            result["verified"] = result["verified_value"] == value
            result["success"] = bool(result["verified"])
        else:
            result["verified"] = False
            result["message"] = "Saved by Frigate. Restart required before runtime value can be verified."
        return result

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
