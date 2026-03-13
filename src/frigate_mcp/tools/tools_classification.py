"""Object classification tools for Frigate (faces, license plates)."""

from __future__ import annotations

import base64
from typing import Annotated, Any

from pydantic import Field


def register_classification_tools(mcp: Any, client: Any) -> None:
    """Register Frigate object classification tools."""

    # ------------------------------------------------------------------ #
    # Faces
    # ------------------------------------------------------------------ #

    @mcp.tool()
    async def get_faces() -> dict[str, Any]:
        """Get all known face names and their face count.

        Returns a dictionary mapping person names to their number of
        stored face images.
        """
        faces = await client.get_faces()
        return {"success": True, "faces": faces}

    @mcp.tool()
    async def get_faces_by_name(
        name: Annotated[str, Field(description="Person name")],
    ) -> dict[str, Any]:
        """Get stored face images for a specific person."""
        faces = await client.get_faces_by_name(name)
        return {"success": True, "name": name, "faces": faces}

    @mcp.tool()
    async def delete_face(
        name: Annotated[str, Field(description="Person name")],
        face_id: Annotated[str, Field(description="Face image ID to delete")],
    ) -> dict[str, Any]:
        """Delete a stored face image for a person."""
        result = await client.delete_face(name, face_id)
        return {"success": True, "result": result}

    # ------------------------------------------------------------------ #
    # License Plates
    # ------------------------------------------------------------------ #

    @mcp.tool()
    async def get_license_plates() -> dict[str, Any]:
        """Get all known license plates and their associated names."""
        plates = await client.get_license_plates()
        return {"success": True, "license_plates": plates}

    @mcp.tool()
    async def get_license_plates_by_name(
        name: Annotated[str, Field(description="Known name for the plate owner")],
    ) -> dict[str, Any]:
        """Get license plates associated with a specific name."""
        plates = await client.get_license_plates_by_name(name)
        return {"success": True, "name": name, "license_plates": plates}

    @mcp.tool()
    async def create_license_plate(
        plate: Annotated[str, Field(description="License plate number/text")],
        known_name: Annotated[str, Field(description="Name to associate with this plate")],
    ) -> dict[str, Any]:
        """Register a known license plate with a name.

        When Frigate detects this plate, it will be associated with the
        given name for easier identification.
        """
        result = await client.create_license_plate(plate, known_name)
        return {"success": True, "result": result}

    @mcp.tool()
    async def delete_license_plate(
        plate: Annotated[str, Field(description="License plate number/text to delete")],
    ) -> dict[str, Any]:
        """Delete a known license plate entry."""
        result = await client.delete_license_plate(plate)
        return {"success": True, "result": result}

    # ------------------------------------------------------------------ #
    # Media helpers
    # ------------------------------------------------------------------ #

    @mcp.tool()
    async def get_event_thumbnail(
        event_id: Annotated[str, Field(description="Event ID")],
    ) -> dict[str, Any]:
        """Get the thumbnail image for an event.

        Returns the thumbnail as a base64-encoded JPEG.
        """
        image_bytes = await client.get_thumbnail(event_id)
        b64 = base64.b64encode(image_bytes).decode("ascii")
        return {
            "success": True,
            "event_id": event_id,
            "image_base64": b64,
            "content_type": "image/jpeg",
        }

    @mcp.tool()
    async def get_event_snapshot(
        event_id: Annotated[str, Field(description="Event ID")],
        crop: Annotated[bool | None, Field(default=None, description="Crop to the detected object region")] = None,
        quality: Annotated[int | None, Field(default=None, description="JPEG quality (1-100)")] = None,
    ) -> dict[str, Any]:
        """Get the snapshot image for an event.

        Returns the snapshot as a base64-encoded JPEG. Optionally crop
        to the detected object or adjust quality.
        """
        image_bytes = await client.get_snapshot(
            event_id, crop=crop, quality=quality
        )
        b64 = base64.b64encode(image_bytes).decode("ascii")
        return {
            "success": True,
            "event_id": event_id,
            "image_base64": b64,
            "content_type": "image/jpeg",
        }
