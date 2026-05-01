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

    All endpoints are based on Frigate v0.17.x. Endpoints requiring multipart
    file uploads (e.g. face register/recognize) are intentionally not exposed —
    this client is JSON/binary-read-only by design.
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
        json_body: Any = None,
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

        if not response.content:
            return {"success": True}

        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            return response.json()

        try:
            return response.json()
        except Exception:
            return response.text

    # ------------------------------------------------------------------ #
    # System / Config
    # ------------------------------------------------------------------ #

    async def get_version(self) -> str:
        resp = await self._request("GET", "/api/version")
        return resp if isinstance(resp, str) else str(resp)

    async def get_stats(self) -> dict[str, Any]:
        return await self._request("GET", "/api/stats")

    async def get_stats_history(
        self, *, keys: str | None = None
    ) -> list[dict[str, Any]]:
        params = {"keys": keys} if keys else None
        return await self._request("GET", "/api/stats/history", params=params)

    async def get_config(self) -> dict[str, Any]:
        return await self._request("GET", "/api/config")

    async def get_config_schema(self) -> dict[str, Any]:
        return await self._request("GET", "/api/config/schema.json")

    async def save_config(
        self, config_yaml: str, *, save_option: str = "saveonly"
    ) -> dict[str, Any]:
        """Save config (admin only).

        save_option: "saveonly" or "restart".  Body is YAML (text/plain).
        """
        # Use raw httpx to send text/plain body
        try:
            response = await self.client.request(
                "POST",
                "/api/config/save",
                params={"save_option": save_option},
                content=config_yaml.encode("utf-8"),
                headers={"Content-Type": "text/plain"},
            )
        except httpx.ConnectError as exc:
            raise FrigateConnectionError(str(exc)) from exc
        if response.status_code >= 400:
            raise FrigateAPIError(response.status_code, response.text)
        return response.json()

    async def restart(self) -> dict[str, Any]:
        return await self._request("POST", "/api/restart")

    async def get_logs(self, service: str = "frigate") -> str:
        """Get logs. service can be: frigate, go2rtc, nginx."""
        resp = await self._request("GET", f"/api/logs/{service}", raw=True)
        return resp.text

    async def get_plus_models(
        self, *, filter_by_current_model_detector: bool = False
    ) -> dict[str, Any]:
        params = {"filterByCurrentModelDetector": filter_by_current_model_detector}
        return await self._request("GET", "/api/plus/models", params=params)

    async def get_recognized_license_plates(
        self, *, split_joined: int | None = None
    ) -> list[str]:
        params: dict[str, Any] = {}
        if split_joined is not None:
            params["split_joined"] = split_joined
        return await self._request(
            "GET", "/api/recognized_license_plates", params=params
        )

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

    async def get_events_by_ids(self, ids: list[str]) -> list[dict[str, Any]]:
        return await self._request(
            "GET", "/api/event_ids", params={"ids": ",".join(ids)}
        )

    async def explore_events(self) -> list[dict[str, Any]]:
        return await self._request("GET", "/api/events/explore")

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
        if retain:
            return await self._request(
                "POST", f"/api/events/{event_id}/retain"
            )
        return await self._request(
            "DELETE", f"/api/events/{event_id}/retain"
        )

    async def set_sub_label(
        self,
        event_id: str,
        sub_label: str,
        *,
        sub_label_score: float | None = None,
        camera: str | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"subLabel": sub_label}
        if sub_label_score is not None:
            body["subLabelScore"] = sub_label_score
        if camera is not None:
            body["camera"] = camera
        return await self._request(
            "POST", f"/api/events/{event_id}/sub_label", json_body=body
        )

    async def set_recognized_license_plate(
        self,
        event_id: str,
        plate: str,
        *,
        plate_score: float | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"recognizedLicensePlate": plate}
        if plate_score is not None:
            body["recognizedLicensePlateScore"] = plate_score
        return await self._request(
            "POST",
            f"/api/events/{event_id}/recognized_license_plate",
            json_body=body,
        )

    async def set_event_attributes(
        self, event_id: str, attributes: list[str]
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            f"/api/events/{event_id}/attributes",
            json_body={"attributes": attributes},
        )

    async def set_description(
        self, event_id: str, description: str
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            f"/api/events/{event_id}/description",
            json_body={"description": description},
        )

    async def regenerate_description(
        self,
        event_id: str,
        *,
        source: str | None = None,
        force: bool | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if source is not None:
            params["source"] = source
        if force is not None:
            params["force"] = force
        return await self._request(
            "PUT",
            f"/api/events/{event_id}/description/regenerate",
            params=params or None,
        )

    async def create_event(
        self,
        camera: str,
        label: str,
        *,
        sub_label: str | None = None,
        score: float | None = None,
        duration: int | None = None,
        include_recording: bool | None = None,
        draw: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {}
        if sub_label is not None:
            body["sub_label"] = sub_label
        if score is not None:
            body["score"] = score
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

    async def get_camera_label_best(
        self, camera: str, label: str, *, height: int | None = None
    ) -> bytes:
        params: dict[str, Any] = {}
        if height is not None:
            params["h"] = height
        resp = await self._request(
            "GET", f"/api/{camera}/{label}/best.jpg", params=params, raw=True
        )
        return resp.content

    # ------------------------------------------------------------------ #
    # Labels / Timeline
    # ------------------------------------------------------------------ #

    async def get_labels(self, camera: str | None = None) -> list[str]:
        params = {"camera": camera} if camera else None
        return await self._request("GET", "/api/labels", params=params)

    async def get_sub_labels(
        self, *, split_joined: int | None = None
    ) -> list[str]:
        params: dict[str, Any] = {}
        if split_joined is not None:
            params["split_joined"] = split_joined
        return await self._request("GET", "/api/sub_labels", params=params)

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

    async def get_timeline_hourly(
        self,
        *,
        cameras: str | None = None,
        labels: str | None = None,
        before: float | None = None,
        after: float | None = None,
        timezone: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {}
        for key, val in {
            "cameras": cameras,
            "labels": labels,
            "before": before,
            "after": after,
            "timezone": timezone,
        }.items():
            if val is not None:
                params[key] = val
        return await self._request("GET", "/api/timeline/hourly", params=params)

    # ------------------------------------------------------------------ #
    # Review
    # ------------------------------------------------------------------ #

    async def get_review(
        self,
        *,
        cameras: str | None = None,
        labels: str | None = None,
        zones: str | None = None,
        reviewed: int | None = None,
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

    async def get_review_by_id(self, review_id: str) -> dict[str, Any]:
        return await self._request("GET", f"/api/review/{review_id}")

    async def get_review_by_event(self, event_id: str) -> dict[str, Any]:
        return await self._request("GET", f"/api/review/event/{event_id}")

    async def get_reviews_by_ids(self, ids: list[str]) -> list[dict[str, Any]]:
        return await self._request(
            "GET", "/api/review_ids", params={"ids": ",".join(ids)}
        )

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

    async def mark_reviewed(
        self, review_ids: list[str], reviewed: bool = True
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/api/reviews/viewed",
            json_body={"ids": review_ids, "reviewed": reviewed},
        )

    async def unmark_review_viewed(self, review_id: str) -> dict[str, Any]:
        return await self._request("DELETE", f"/api/review/{review_id}/viewed")

    async def delete_reviews(self, review_ids: list[str]) -> dict[str, Any]:
        return await self._request(
            "POST", "/api/reviews/delete", json_body={"ids": review_ids}
        )

    async def get_motion_activity(
        self,
        *,
        cameras: str | None = None,
        after: float | None = None,
        before: float | None = None,
        scale: int | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {}
        for key, val in {
            "cameras": cameras,
            "after": after,
            "before": before,
            "scale": scale,
        }.items():
            if val is not None:
                params[key] = val
        return await self._request(
            "GET", "/api/review/activity/motion", params=params
        )

    async def summarize_reviews(
        self, start_ts: float, end_ts: float
    ) -> dict[str, Any]:
        return await self._request(
            "POST", f"/api/review/summarize/start/{start_ts}/end/{end_ts}"
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

    async def get_recordings(
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
            "GET", f"/api/{camera}/recordings", params=params
        )

    async def get_recording_storage(self) -> dict[str, Any]:
        return await self._request("GET", "/api/recordings/storage")

    async def get_recordings_unavailable(
        self,
        *,
        cameras: str | None = None,
        after: float | None = None,
        before: float | None = None,
        scale: int | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {}
        for key, val in {
            "cameras": cameras,
            "after": after,
            "before": before,
            "scale": scale,
        }.items():
            if val is not None:
                params[key] = val
        return await self._request(
            "GET", "/api/recordings/unavailable", params=params
        )

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
        *,
        playback: str | None = None,
        source: str | None = None,
        name: str | None = None,
        image_path: str | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {}
        if playback is not None:
            body["playback"] = playback
        if source is not None:
            body["source"] = source
        if name is not None:
            body["name"] = name
        if image_path is not None:
            body["image_path"] = image_path
        return await self._request(
            "POST",
            f"/api/export/{camera}/start/{start}/end/{end}",
            json_body=body,
        )

    async def delete_export(self, export_id: str) -> dict[str, Any]:
        return await self._request("DELETE", f"/api/export/{export_id}")

    async def rename_export(
        self, export_id: str, name: str
    ) -> dict[str, Any]:
        return await self._request(
            "PATCH",
            f"/api/export/{export_id}/rename",
            json_body={"name": name},
        )

    # ------------------------------------------------------------------ #
    # Faces
    # ------------------------------------------------------------------ #

    async def get_faces(self) -> dict[str, list[str]]:
        return await self._request("GET", "/api/faces")

    async def create_face_folder(self, name: str) -> dict[str, Any]:
        return await self._request("POST", f"/api/faces/{name}/create")

    async def delete_face_images(
        self, name: str, image_ids: list[str]
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            f"/api/faces/{name}/delete",
            json_body={"ids": image_ids},
        )

    async def rename_face(self, old_name: str, new_name: str) -> dict[str, Any]:
        return await self._request(
            "PUT",
            f"/api/faces/{old_name}/rename",
            json_body={"new_name": new_name},
        )

    async def reprocess_face(self, training_file: str) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/api/faces/reprocess",
            json_body={"training_file": training_file},
        )

    # ------------------------------------------------------------------ #
    # License Plate Recognition
    # ------------------------------------------------------------------ #

    async def reprocess_event_license_plate(self, event_id: str) -> dict[str, Any]:
        return await self._request(
            "PUT", "/api/lpr/reprocess", params={"event_id": event_id}
        )
