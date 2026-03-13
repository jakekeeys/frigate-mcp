"""Camera tools for Frigate."""

from __future__ import annotations

import base64
from typing import Annotated, Any

from pydantic import Field


def register_camera_tools(mcp: Any, client: Any) -> None:
    """Register Frigate camera tools."""

    @mcp.tool()
    async def get_latest_frame(
        camera: Annotated[str, Field(description="Camera name to get the latest frame from")],
        height: Annotated[int | None, Field(default=None, description="Resize image to this height in pixels")] = None,
    ) -> dict[str, Any]:
        """Get the latest camera frame as a JPEG image.

        Returns the image as a base64-encoded string. Use this to see
        what a camera is currently viewing.
        """
        image_bytes = await client.get_latest_frame(camera, height=height)
        b64 = base64.b64encode(image_bytes).decode("ascii")
        return {
            "success": True,
            "camera": camera,
            "image_base64": b64,
            "content_type": "image/jpeg",
        }

    @mcp.tool()
    async def get_ptz_info(
        camera: Annotated[str, Field(description="Camera name")],
    ) -> dict[str, Any]:
        """Get PTZ (Pan-Tilt-Zoom) capabilities and presets for a camera.

        Only works for cameras with PTZ support configured.
        """
        info = await client.get_ptz_info(camera)
        return {"success": True, "camera": camera, "ptz_info": info}

    @mcp.tool()
    async def ptz_command(
        camera: Annotated[str, Field(description="Camera name")],
        action: Annotated[str, Field(description="PTZ action: 'move', 'zoom', 'preset', 'stop'")],
        pan: Annotated[float | None, Field(default=None, description="Pan speed/amount (-1 to 1)")] = None,
        tilt: Annotated[float | None, Field(default=None, description="Tilt speed/amount (-1 to 1)")] = None,
        zoom: Annotated[float | None, Field(default=None, description="Zoom speed/amount (-1 to 1)")] = None,
        preset: Annotated[str | None, Field(default=None, description="Preset name to move to")] = None,
    ) -> dict[str, Any]:
        """Send a PTZ command to a camera.

        Actions:
        - 'move': Move with pan/tilt values
        - 'zoom': Zoom with zoom value
        - 'preset': Go to a named preset
        - 'stop': Stop current PTZ movement
        """
        result = await client.ptz_command(
            camera,
            action,
            pan=pan,
            tilt=tilt,
            zoom=zoom,
            preset=preset,
        )
        return {"success": True, "result": result}
