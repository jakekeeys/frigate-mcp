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

    # ------------------------------------------------------------------ #
    # Frigate 0.18+
    # ------------------------------------------------------------------ #

    @mcp.tool()
    async def set_camera_feature(
        camera: Annotated[str, Field(description="Camera name, or '*' for all cameras (required for feature='profile')")],
        feature: Annotated[str, Field(description="enabled, detect, motion, recordings, snapshots, audio, audio_transcription, notifications, review_alerts, review_detections, object_descriptions, review_descriptions, improve_contrast, ptz_autotracker, birdseye, birdseye_mode, motion_contour_area, motion_threshold, motion_mask, object_mask, zone, profile")],
        value: Annotated[str, Field(description="'ON'/'OFF' for toggles; CONTINUOUS/MOTION/OBJECTS for birdseye_mode; integer for motion_*; profile name or 'none' for profile")],
        sub_command: Annotated[str | None, Field(default=None, description="Mask or zone name; required for motion_mask, object_mask, zone; rejected otherwise")] = None,
    ) -> dict[str, Any]:
        """0.18+: Toggle or set a camera feature over HTTP (same semantics as the MQTT topics).

        Use this to turn detection/recording/snapshots/etc. on or off, enable or
        disable a zone or mask, tune motion, or switch the active profile.
        """
        result = await client.set_camera_feature(camera, feature, value, sub_command=sub_command)
        return {"success": True, "result": result}

    @mcp.tool()
    async def start_vlm_monitor(
        camera: Annotated[str, Field(description="Camera to watch")],
        condition: Annotated[str, Field(description="Natural-language condition to watch for, e.g. 'a person opens the gate'")],
        max_duration_minutes: Annotated[int | None, Field(default=None, description="Stop watching after this many minutes (default 60)")] = None,
        labels: Annotated[list[str] | None, Field(default=None, description="Only consider these object labels")] = None,
        zones: Annotated[list[str] | None, Field(default=None, description="Only consider objects in these zones")] = None,
    ) -> dict[str, Any]:
        """0.18+: Ask the configured vision GenAI model to watch a camera for a condition and notify when it happens.

        Requires a GenAI chat provider with vision. Only one monitor runs at a time.
        """
        result = await client.start_vlm_monitor(
            camera, condition, max_duration_minutes=max_duration_minutes, labels=labels, zones=zones
        )
        return {"success": True, "result": result}

    @mcp.tool()
    async def get_vlm_monitor() -> dict[str, Any]:
        """0.18+: Get the active VLM monitor job, if any."""
        result = await client.get_vlm_monitor()
        return {"success": True, "monitor": result}

    @mcp.tool()
    async def cancel_vlm_monitor() -> dict[str, Any]:
        """0.18+: Cancel the active VLM monitor job."""
        result = await client.cancel_vlm_monitor()
        return {"success": True, "result": result}
