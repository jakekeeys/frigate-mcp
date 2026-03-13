"""Async HTTP client for the Frigate API."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from frigate_mcp.config import get_settings

logger = logging.getLogger(__name__)


class FrigateAPIError(Exception):
    """Raised when a Frigate API call fails."""

    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        super().__init__(f"Frigate API error {status_code}: {message}")


class FrigateConnectionError(Exception):
    """Raised when we cannot connect to Frigate."""


class FrigateClient:
    """Async HTTP client for the Frigate NVR API.

    Follows the same pattern as ha-mcp's HomeAssistantClient:
    - httpx.AsyncClient with base_url
    - Centralised _request() with error handling
    - High-level typed methods for every endpoint
    """

    def __init__(
        self,
        base_url: str | None = None,
        timeout: int | None = None,
    ) -> None:
        settings = get_settings()
        self.base_url = (base_url or settings.frigate_url).rstrip("/")
        self.timeout = timeout or settings.timeout

        self._client: httpx.AsyncClient | None = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(self.timeout),
                headers={"Content-Type": "application/json"},
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    # ------------------------------------------------------------------ #
    # Core request helper
    # ------------------------------------------------------------------ #

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        raw: bool = False,
    ) -> Any:
        """Send an HTTP request to Frigate and return the JSON response.

        If *raw* is True the httpx.Response object is returned instead
        (useful for binary payloads like images).
        """
        try:
            response = await self.client.request(
                method,
                path,
                params=params,
                json=json_body,
            )
        except httpx.ConnectError as exc:
            raise FrigateConnectionError(
                f"Cannot connect to Frigate at {self.base_url}: {exc}"
            ) from exc
        except httpx.TimeoutException as exc:
            raise FrigateConnectionError(
                f"Timeout connecting to Frigate at {self.base_url}: {exc}"
            ) from exc

        if raw:
            if response.status_code >= 400:
                raise FrigateAPIError(response.status_code, response.text)
            return response

        if response.status_code >= 400:
            raise FrigateAPIError(response.status_code, response.text)

        # Some Frigate endpoints return empty 200
        if not response.content:
            return {"success": True}

        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            return response.json()

        # Try JSON first, fall back to plain text
        try:
            return response.json()
        except Exception:
            return response.text

    # ------------------------------------------------------------------ #
    # System / Config
    # ------------------------------------------------------------------ #

    async def get_version(self) -> str:
        resp = await self._request("GET", "/api/version")
        # Version endpoint returns plain text
        return resp if isinstance(resp, str) else str(resp)

    async def get_stats(self) -> dict[str, Any]:
        return await self._request("GET", "/api/stats")

    async def get_config(self) -> dict[str, Any]:
        return await self._request("GET", "/api/config")

    async def save_config(self, config: dict[str, Any]) -> dict[str, Any]:
        return await self._request("POST", "/api/config/save", json_body=config)

    async def restart(self) -> dict[str, Any]:
        return await self._request("POST", "/api/restart")

    async def get_logs(self, service: str = "frigate") -> str:
        """Get logs. service can be: frigate, go2rtc, nginx."""
        resp = await self._request("GET", f"/api/logs/{service}", raw=True)
        return resp.text

    # ------------------------------------------------------------------ #
    # Events
    # ------------------------------------------------------------------ #

    async def get_events(
        self,
        *,
        camera: str | None = None,
        cameras: str | None = None,
        label: str | None = None,
        labels: str | None = None,
        sub_label: str | None = None,
        sub_labels: str | None = None,
        zone: str | None = None,
        zones: str | None = None,
        after: float | None = None,
        before: float | None = None,
        has_clip: bool | None = None,
        has_snapshot: bool | None = None,
        in_progress: bool | None = None,
        include_thumbnails: bool | None = None,
        favorites: bool | None = None,
        limit: int | None = None,
        sort: str | None = None,
        timezone: str | None = None,
        min_score: float | None = None,
        max_score: float | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {}
        for key, val in {
            "camera": camera,
            "cameras": cameras,
            "label": label,
            "labels": labels,
            "sub_label": sub_label,
            "sub_labels": sub_labels,
            "zone": zone,
            "zones": zones,
            "after": after,
            "before": before,
            "has_clip": has_clip,
            "has_snapshot": has_snapshot,
            "in_progress": in_progress,
            "include_thumbnails": include_thumbnails,
            "favorites": favorites,
            "limit": limit,
            "sort": sort,
            "timezone": timezone,
            "min_score": min_score,
            "max_score": max_score,
        }.items():
            if val is not None:
                params[key] = val
        return await self._request("GET", "/api/events", params=params)

    async def get_event(self, event_id: str) -> dict[str, Any]:
        return await self._request("GET", f"/api/events/{event_id}")

    async def search_events(
        self,
        query: str,
        *,
        cameras: str | None = None,
        labels: str | None = None,
        zones: str | None = None,
        after: float | None = None,
        before: float | None = None,
        include_thumbnails: bool | None = None,
        limit: int | None = None,
        search_type: str | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"query": query}
        for key, val in {
            "cameras": cameras,
            "labels": labels,
            "zones": zones,
            "after": after,
            "before": before,
            "include_thumbnails": include_thumbnails,
            "limit": limit,
            "search_type": search_type,
        }.items():
            if val is not None:
                params[key] = val
        return await self._request("GET", "/api/events/search", params=params)

    async def get_event_summary(
        self,
        *,
        timezone: str | None = None,
        has_clip: bool | None = None,
        has_snapshot: bool | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {}
        if timezone:
            params["timezone"] = timezone
        if has_clip is not None:
            params["has_clip"] = has_clip
        if has_snapshot is not None:
            params["has_snapshot"] = has_snapshot
        return await self._request("GET", "/api/events/summary", params=params)

    async def delete_event(self, event_id: str) -> dict[str, Any]:
        return await self._request("DELETE", f"/api/events/{event_id}")

    async def retain_event(self, event_id: str, retain: bool) -> dict[str, Any]:
        return await self._request(
            "POST",
            f"/api/events/{event_id}/retain",
            json_body={"retain": retain},
        )

    async def set_sub_label(
        self, event_id: str, sub_label: str
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            f"/api/events/{event_id}/sub_label",
            json_body={"subLabel": sub_label},
        )

    async def set_description(
        self, event_id: str, description: str
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            f"/api/events/{event_id}/description",
            json_body={"description": description},
        )

    async def create_event(
        self,
        camera: str,
        label: str,
        *,
        sub_label: str | None = None,
        duration: int | None = None,
        include_recording: bool | None = None,
        draw: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"label": label}
        if sub_label:
            body["sub_label"] = sub_label
        if duration is not None:
            body["duration"] = duration
        if include_recording is not None:
            body["include_recording"] = include_recording
        if draw is not None:
            body["draw"] = draw
        return await self._request(
            "POST", f"/api/events/{camera}/{label}/create", json_body=body
        )

    async def end_event(self, event_id: str) -> dict[str, Any]:
        return await self._request("PUT", f"/api/events/{event_id}/end")

    async def mark_event_as_false_positive(
        self, event_id: str
    ) -> dict[str, Any]:
        return await self._request(
            "PUT", f"/api/events/{event_id}/false_positive"
        )

    # ------------------------------------------------------------------ #
    # Media / Snapshots / Thumbnails
    # ------------------------------------------------------------------ #

    async def get_thumbnail(self, event_id: str) -> bytes:
        resp = await self._request(
            "GET", f"/api/events/{event_id}/thumbnail.jpg", raw=True
        )
        return resp.content

    async def get_snapshot(
        self, event_id: str, *, crop: bool | None = None, quality: int | None = None
    ) -> bytes:
        params: dict[str, Any] = {}
        if crop is not None:
            params["crop"] = 1 if crop else 0
        if quality is not None:
            params["quality"] = quality
        resp = await self._request(
            "GET", f"/api/events/{event_id}/snapshot.jpg", params=params, raw=True
        )
        return resp.content

    async def get_latest_frame(
        self, camera: str, *, height: int | None = None
    ) -> bytes:
        params: dict[str, Any] = {}
        if height is not None:
            params["h"] = height
        resp = await self._request(
            "GET", f"/api/{camera}/latest.jpg", params=params, raw=True
        )
        return resp.content

    # ------------------------------------------------------------------ #
    # Labels
    # ------------------------------------------------------------------ #

    async def get_labels(self, camera: str | None = None) -> list[str]:
        path = f"/api/{camera}/labels" if camera else "/api/labels"
        return await self._request("GET", path)

    async def get_sub_labels(self) -> list[str]:
        return await self._request("GET", "/api/sub_labels")

    # ------------------------------------------------------------------ #
    # Timeline
    # ------------------------------------------------------------------ #

    async def get_timeline(
        self,
        *,
        camera: str | None = None,
        source_id: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {}
        if camera:
            params["camera"] = camera
        if source_id:
            params["source_id"] = source_id
        if limit is not None:
            params["limit"] = limit
        return await self._request("GET", "/api/timeline", params=params)

    # ------------------------------------------------------------------ #
    # Review
    # ------------------------------------------------------------------ #

    async def get_review(
        self,
        *,
        cameras: str | None = None,
        labels: str | None = None,
        zones: str | None = None,
        reviewed: bool | None = None,
        after: float | None = None,
        before: float | None = None,
        limit: int | None = None,
        severity: str | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {}
        for key, val in {
            "cameras": cameras,
            "labels": labels,
            "zones": zones,
            "reviewed": reviewed,
            "after": after,
            "before": before,
            "limit": limit,
            "severity": severity,
        }.items():
            if val is not None:
                params[key] = val
        return await self._request("GET", "/api/review", params=params)

    async def get_review_summary(
        self,
        *,
        cameras: str | None = None,
        labels: str | None = None,
        zones: str | None = None,
        timezone: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if cameras:
            params["cameras"] = cameras
        if labels:
            params["labels"] = labels
        if zones:
            params["zones"] = zones
        if timezone:
            params["timezone"] = timezone
        return await self._request("GET", "/api/review/summary", params=params)

    async def mark_reviewed(self, review_ids: list[str]) -> dict[str, Any]:
        return await self._request(
            "POST", "/api/reviews/viewed", json_body={"ids": review_ids}
        )

    async def delete_reviews(self, review_ids: list[str]) -> dict[str, Any]:
        return await self._request(
            "POST", "/api/reviews/delete", json_body={"ids": review_ids}
        )

    async def get_motion_activity(
        self,
        camera: str,
        *,
        after: float | None = None,
        before: float | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {}
        if after is not None:
            params["after"] = after
        if before is not None:
            params["before"] = before
        return await self._request(
            "GET", f"/api/{camera}/motion/activity", params=params
        )

    # ------------------------------------------------------------------ #
    # Recordings
    # ------------------------------------------------------------------ #

    async def get_recording_summary(
        self, camera: str, *, timezone: str | None = None
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {}
        if timezone:
            params["timezone"] = timezone
        return await self._request(
            "GET", f"/api/{camera}/recordings/summary", params=params
        )

    async def get_recording_storage(self) -> dict[str, Any]:
        return await self._request("GET", "/api/recordings/storage")

    # ------------------------------------------------------------------ #
    # Exports
    # ------------------------------------------------------------------ #

    async def get_exports(self) -> list[dict[str, Any]]:
        return await self._request("GET", "/api/exports")

    async def get_export(self, export_id: str) -> dict[str, Any]:
        return await self._request("GET", f"/api/exports/{export_id}")

    async def create_export(
        self,
        camera: str,
        start: float,
        end: float,
        name: str | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "camera": camera,
            "start": start,
            "end": end,
        }
        if name:
            body["name"] = name
        return await self._request("POST", "/api/export", json_body=body)

    async def delete_export(self, export_id: str) -> dict[str, Any]:
        return await self._request("DELETE", f"/api/exports/{export_id}")

    async def rename_export(
        self, export_id: str, name: str
    ) -> dict[str, Any]:
        return await self._request(
            "PATCH",
            f"/api/exports/{export_id}",
            json_body={"name": name},
        )

    # ------------------------------------------------------------------ #
    # Notifications
    # ------------------------------------------------------------------ #

    async def get_notifications(
        self, *, limit: int | None = None, offset: int | None = None
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {}
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        return await self._request("GET", "/api/notifications", params=params)

    async def mark_notifications_read(
        self, notification_ids: list[str]
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/api/notifications/read",
            json_body={"ids": notification_ids},
        )

    # ------------------------------------------------------------------ #
    # Object Classification – Faces
    # ------------------------------------------------------------------ #

    async def get_faces(self) -> dict[str, Any]:
        return await self._request("GET", "/api/faces")

    async def get_faces_by_name(self, name: str) -> list[dict[str, Any]]:
        return await self._request("GET", f"/api/faces/{name}")

    async def delete_face(self, name: str, face_id: str) -> dict[str, Any]:
        return await self._request(
            "DELETE", f"/api/faces/{name}/{face_id}"
        )

    # ------------------------------------------------------------------ #
    # Object Classification – License Plates
    # ------------------------------------------------------------------ #

    async def get_license_plates(self) -> dict[str, Any]:
        return await self._request("GET", "/api/license_plates")

    async def get_license_plates_by_name(
        self, name: str
    ) -> list[dict[str, Any]]:
        return await self._request("GET", f"/api/license_plates/{name}")

    async def create_license_plate(
        self, plate: str, known_name: str
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/api/license_plates",
            json_body={"plate": plate, "name": known_name},
        )

    async def delete_license_plate(self, plate: str) -> dict[str, Any]:
        return await self._request("DELETE", f"/api/license_plates/{plate}")

    # ------------------------------------------------------------------ #
    # PTZ
    # ------------------------------------------------------------------ #

    async def get_ptz_info(self, camera: str) -> dict[str, Any]:
        return await self._request("GET", f"/api/{camera}/ptz/info")

    async def ptz_command(
        self,
        camera: str,
        action: str,
        *,
        pan: float | None = None,
        tilt: float | None = None,
        zoom: float | None = None,
        preset: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"action": action}
        if pan is not None:
            params["pan"] = pan
        if tilt is not None:
            params["tilt"] = tilt
        if zoom is not None:
            params["zoom"] = zoom
        if preset is not None:
            params["preset"] = preset
        return await self._request(
            "POST", f"/api/{camera}/ptz", params=params
        )
