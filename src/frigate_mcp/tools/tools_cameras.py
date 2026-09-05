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
    async def get_camera_label_best(
        camera: Annotated[str, Field(description="Camera name")],
        label: Annotated[str, Field(description="Object label (person, car, dog, etc.), or 'any' for the latest event of any label")],
    ) -> dict[str, Any]:
        """Get the most recent 'best' thumbnail for a camera + label combo.

        Frigate keeps a rolling best snapshot per (camera, label). Useful for
        a quick "what's the latest person seen on the front door?" query.
        """
        image_bytes = await client.get_camera_label_best(camera, label)
        b64 = base64.b64encode(image_bytes).decode("ascii")
        return {
            "success": True,
            "camera": camera,
            "label": label,
            "image_base64": b64,
            "content_type": "image/jpeg",
        }

    @mcp.tool()
    async def get_ptz_info(
        camera: Annotated[str, Field(description="Camera name")],
    ) -> dict[str, Any]:
        """Get a camera's PTZ capabilities and presets via ONVIF (read-only; PTZ control is MQTT-only)."""
        info = await client.get_ptz_info(camera)
        return {"success": True, "camera": camera, "ptz": info}
