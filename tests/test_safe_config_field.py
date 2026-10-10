"""Safe config field helpers and MCP tool behavior (no live Frigate calls)."""
from __future__ import annotations

import asyncio
from typing import Any

import pytest

from frigate_mcp.tools.tools_system import _config_field, _nested_field, register_system_tools


def test_scalar_path():
    config = {"genai": {"model": "old"}, "cameras": {"front": {"detect": {"enabled": True}}}}
    assert _config_field(config, "genai.model") == "old"
    assert _config_field(config, "cameras.front.detect.enabled") is True
    assert _nested_field("genai.model", "new") == {"genai": {"model": "new"}}


@pytest.mark.parametrize("path", ["", "genai..model", "genai.token", "mqtt.password",
                                  "cameras.front.ffmpeg.inputs.0.path", "cameras.front",
                                  "genai.unknown", "cameras.front.detect.__class__"])
def test_rejected_paths(path):
    with pytest.raises(ValueError):
        _config_field({"genai": {"model": "x", "token": "hidden"},
                       "cameras": {"front": {"detect": {"enabled": True}}}}, path)


class FakeMCP:
    def __init__(self):
        self.tools = {}

    def tool(self):
        def register(fn):
            self.tools[fn.__name__] = fn
            return fn
        return register


class FakeClient:
    def __init__(self):
        self.config = {"genai": {"model": "old"}}
        self.calls = []

    async def get_config(self):
        return self.config

    async def set_config(self, config_data, *, requires_restart):
        self.calls.append((config_data, requires_restart))
        if not requires_restart:
            self.config = {"genai": {"model": config_data["genai"]["model"]}}
        return {"success": True}


def test_update_flow():
    async def check():
        server, client = FakeMCP(), FakeClient()
        register_system_tools(server, client)
        update = server.tools["update_config_field"]
        read = server.tools["get_config_field"]
        assert (await read("genai.model"))["value"] == "old"
        preview = await update("genai.model", "new", "old")
        assert preview["dry_run"] and not client.calls
        conflict = await update("genai.model", "new", "wrong", dry_run=False)
        assert conflict["error"] == "config_conflict" and not client.calls
        with pytest.raises(ValueError):
            await update("genai.model", 123, "old", dry_run=False)
        with pytest.raises(ValueError):
            await update("genai.token", "x", "y", dry_run=False)
        saved = await update("genai.model", "new", "old", dry_run=False, requires_restart=False)
        assert saved["verified"] and saved["success"]
        assert client.calls == [({"genai": {"model": "new"}}, False)]
        pending = await update("genai.model", "latest", "new", dry_run=False)
        assert pending["success"] and pending["verified"] is False
    asyncio.run(check())
