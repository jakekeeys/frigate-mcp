"""Classification tools for Frigate (faces, license plates) and event media."""

from __future__ import annotations

import base64
from typing import Annotated, Any

from pydantic import Field


def register_classification_tools(mcp: Any, client: Any) -> None:
    """Register Frigate classification + event-media tools."""

    # ------------------------------------------------------------------ #
    # Faces
    # ------------------------------------------------------------------ #

    @mcp.tool()
    async def get_faces() -> dict[str, Any]:
        """Get all registered face names and their image filenames.

        Returns a dictionary mapping each person name to a list of stored
        image filenames in their face folder.
        """
        faces = await client.get_faces()
        return {"success": True, "faces": faces}

    @mcp.tool()
    async def create_face_folder(
        name: Annotated[str, Field(description="Person name (folder will be created for their face images)")],
    ) -> dict[str, Any]:
        """Create a face folder for a new person.

        Frigate face recognition must be enabled. After creation, training
        images can be added by uploading them to Frigate's UI (multipart
        upload — not exposed by this MCP server).
        """
        result = await client.create_face_folder(name)
        return {"success": True, "result": result}

    @mcp.tool()
    async def delete_face_images(
        name: Annotated[str, Field(description="Person name")],
        image_ids: Annotated[list[str], Field(description="List of image filenames to delete from this person's folder")],
    ) -> dict[str, Any]:
        """Delete one or more stored face images for a person.

        Deleting all images for a name effectively removes the person.
        """
        result = await client.delete_face_images(name, image_ids)
        return {"success": True, "result": result}

    @mcp.tool()
    async def rename_face(
        old_name: Annotated[str, Field(description="Existing person name to rename")],
        new_name: Annotated[str, Field(description="New name for the person")],
    ) -> dict[str, Any]:
        """Rename a registered face."""
        result = await client.rename_face(old_name, new_name)
        return {"success": True, "result": result}

    @mcp.tool()
    async def reprocess_face(
        training_file: Annotated[str, Field(description="Filename of a training image in Frigate's faces/train directory")],
    ) -> dict[str, Any]:
        """Reprocess a face training image to update predictions."""
        result = await client.reprocess_face(training_file)
        return {"success": True, "result": result}

    # ------------------------------------------------------------------ #
    # License plate recognition
    # ------------------------------------------------------------------ #

    @mcp.tool()
    async def get_recognized_license_plates(
        split_joined: Annotated[int | None, Field(default=None, description="If 1, split joined plates (e.g. 'ABC123,XYZ789') into separate entries")] = None,
    ) -> dict[str, Any]:
        """List all recognized license plates that have appeared in events."""
        plates = await client.get_recognized_license_plates(split_joined=split_joined)
        return {"success": True, "license_plates": plates}

    @mcp.tool()
    async def reprocess_event_license_plate(
        event_id: Annotated[str, Field(description="Event ID to re-run LPR on")],
    ) -> dict[str, Any]:
        """Re-run license plate recognition on an event's snapshot."""
        result = await client.reprocess_event_license_plate(event_id)
        return {"success": True, "result": result}

    # ------------------------------------------------------------------ #
    # Event media (thumbnail / snapshot)
    # ------------------------------------------------------------------ #

    @mcp.tool()
    async def get_event_thumbnail(
        event_id: Annotated[str, Field(description="Event ID")],
    ) -> dict[str, Any]:
        """Get the thumbnail image for an event as base64-encoded JPEG."""
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
        """Get the snapshot image for an event as base64-encoded JPEG."""
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

    @mcp.tool()
    async def get_event_preview_gif(
        event_id: Annotated[str, Field(description="Event ID")],
    ) -> dict[str, Any]:
        """Get an animated GIF preview of an event (first 20s max) as base64."""
        image_bytes = await client.get_event_preview_gif(event_id)
        return {
            "success": True,
            "event_id": event_id,
            "image_base64": base64.b64encode(image_bytes).decode("ascii"),
            "content_type": "image/gif",
        }

    @mcp.tool()
    async def get_event_clean_snapshot(
        event_id: Annotated[str, Field(description="Event ID")],
    ) -> dict[str, Any]:
        """Get the clean (no bounding box / timestamp overlay) event snapshot as base64 WebP."""
        image_bytes = await client.get_event_clean_snapshot(event_id)
        return {
            "success": True,
            "event_id": event_id,
            "image_base64": base64.b64encode(image_bytes).decode("ascii"),
            "content_type": "image/webp",
        }

    # ------------------------------------------------------------------ #
    # Semantic search / audio
    # ------------------------------------------------------------------ #

    @mcp.tool()
    async def transcribe_event_audio(
        event_id: Annotated[str, Field(description="Event ID of a speech event")],
    ) -> dict[str, Any]:
        """Start audio transcription for an event. Async: returns immediately; result lands on the event later.

        Requires audio_transcription enabled on the event's camera.
        """
        result = await client.transcribe_event_audio(event_id)
        return {"success": True, "result": result}

    @mcp.tool()
    async def reindex_embeddings() -> dict[str, Any]:
        """Rebuild all semantic-search embeddings for tracked objects. Long-running; errors if already in progress."""
        result = await client.reindex_embeddings()
        return {"success": True, "result": result}
