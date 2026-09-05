"""Async HTTP client for the Frigate API."""

from __future__ import annotations

import logging
import re
from typing import Any

import httpx

from frigate_mcp.config import get_settings

logger = logging.getLogger(__name__)


def _flag(val: bool | None) -> int | None:
    """Frigate types boolean query flags as Optional[int]; httpx would send 'true'."""
    return None if val is None else int(val)


class FrigateAPIError(Exception):
    """Raised when a Frigate API call fails."""

    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        super().__init__(f"Frigate API error {status_code}: {message}")


class FrigateConnectionError(Exception):
    """Raised when we cannot connect to Frigate."""


class FrigateClient:
    """Async HTTP client for the Frigate NVR API.

    Endpoints are verified against Frigate v0.17.2 and v0.18.0-rc1; 0.18-only
    endpoints are marked. The one 0.18 breaking change (export delete) is gated
    on the connected version. Endpoints requiring multipart
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
        self._version: tuple[int, int] | None = None

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

    async def version_tuple(self) -> tuple[int, int]:
        """(major, minor) of the connected Frigate; fetched once and cached."""
        if self._version is None:
            m = re.match(r"(\d+)\.(\d+)", await self.get_version())
            self._version = (int(m.group(1)), int(m.group(2))) if m else (0, 0)
        return self._version

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

    async def get_logs(
        self,
        service: str = "frigate",
        *,
        start: int | None = None,
        end: int | None = None,
    ) -> dict[str, Any]:
        """Get logs. service can be: frigate, go2rtc, nginx.

        Returns {"totalLines": int, "lines": [...]}; start/end are line offsets.
        """
        params: dict[str, Any] = {}
        if start is not None:
            params["start"] = start
        if end is not None:
            params["end"] = end
        return await self._request("GET", f"/api/logs/{service}", params=params)

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

    async def get_config_raw(self) -> str:
        """Raw config file contents (YAML text)."""
        return await self._request("GET", "/api/config/raw")

    async def set_config(
        self, config_data: dict[str, Any], *, requires_restart: bool = True
    ) -> dict[str, Any]:
        """Partial config update; nested dict is flattened + merged server-side."""
        return await self._request(
            "PUT",
            "/api/config/set",
            json_body={
                "config_data": config_data,
                "requires_restart": int(requires_restart),
            },
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
            "has_clip": _flag(has_clip),
            "has_snapshot": _flag(has_snapshot),
            "in_progress": _flag(in_progress),
            "include_thumbnails": _flag(include_thumbnails),
            "favorites": _flag(favorites),
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
        event_id: str | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"query": query}
        for key, val in {
            "cameras": cameras,
            "labels": labels,
            "zones": zones,
            "after": after,
            "before": before,
            "include_thumbnails": _flag(include_thumbnails),
            "limit": limit,
            "search_type": search_type,
            "event_id": event_id,
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
            params["has_clip"] = _flag(has_clip)
        if has_snapshot is not None:
            params["has_snapshot"] = _flag(has_snapshot)
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
        pre_capture: int | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {}
        if pre_capture is not None:
            body["pre_capture"] = pre_capture
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

    async def end_event(
        self, event_id: str, *, end_time: float | None = None
    ) -> dict[str, Any]:
        return await self._request(
            "PUT", f"/api/events/{event_id}/end", json_body={"end_time": end_time}
        )

    async def mark_event_as_false_positive(
        self, event_id: str
    ) -> dict[str, Any]:
        return await self._request(
            "PUT", f"/api/events/{event_id}/false_positive"
        )

    async def delete_events(self, event_ids: list[str]) -> dict[str, Any]:
        return await self._request(
            "DELETE", "/api/events/", json_body={"event_ids": event_ids}
        )

    async def get_triggers_status(self, camera: str) -> dict[str, Any]:
        return await self._request("GET", f"/api/triggers/status/{camera}")

    async def create_trigger_embedding(
        self,
        camera: str,
        name: str,
        *,
        trigger_type: str,
        data: str,
        threshold: float | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"type": trigger_type, "data": data}
        if threshold is not None:
            body["threshold"] = threshold
        return await self._request(
            "POST",
            "/api/trigger/embedding",
            params={"camera_name": camera, "name": name},
            json_body=body,
        )

    async def update_trigger_embedding(
        self,
        camera: str,
        name: str,
        *,
        trigger_type: str,
        data: str,
        threshold: float | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"type": trigger_type, "data": data}
        if threshold is not None:
            body["threshold"] = threshold
        return await self._request(
            "PUT", f"/api/trigger/embedding/{camera}/{name}", json_body=body
        )

    async def delete_trigger_embedding(
        self, camera: str, name: str
    ) -> dict[str, Any]:
        return await self._request(
            "DELETE", f"/api/trigger/embedding/{camera}/{name}"
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
        self,
        event_id: str,
        *,
        crop: bool | None = None,
        quality: int | None = None,
        height: int | None = None,
        bbox: bool | None = None,
        timestamp: bool | None = None,
    ) -> bytes:
        params: dict[str, Any] = {}
        for key, val in {
            "crop": _flag(crop),
            "quality": quality,
            "height": height,
            "bbox": _flag(bbox),
            "timestamp": _flag(timestamp),
        }.items():
            if val is not None:
                params[key] = val
        resp = await self._request(
            "GET", f"/api/events/{event_id}/snapshot.jpg", params=params, raw=True
        )
        return resp.content

    async def get_latest_frame(
        self, camera: str, *, height: int | None = None
    ) -> bytes:
        params: dict[str, Any] = {}
        if height is not None:
            params["height"] = height
        resp = await self._request(
            "GET", f"/api/{camera}/latest.jpg", params=params, raw=True
        )
        return resp.content

    async def get_camera_label_best(self, camera: str, label: str) -> bytes:
        resp = await self._request(
            "GET", f"/api/{camera}/{label}/best.jpg", raw=True
        )
        return resp.content

    async def get_event_preview_gif(self, event_id: str) -> bytes:
        resp = await self._request(
            "GET", f"/api/events/{event_id}/preview.gif", raw=True
        )
        return resp.content

    async def get_event_clean_snapshot(self, event_id: str) -> bytes:
        resp = await self._request(
            "GET", f"/api/events/{event_id}/snapshot-clean.webp", raw=True
        )
        return resp.content

    async def get_recording_snapshot(
        self,
        camera: str,
        frame_time: float,
        *,
        fmt: str = "jpg",
        height: int | None = None,
    ) -> bytes:
        params: dict[str, Any] = {}
        if height is not None:
            params["height"] = height
        resp = await self._request(
            "GET",
            f"/api/{camera}/recordings/{frame_time}/snapshot.{fmt}",
            params=params,
            raw=True,
        )
        return resp.content

    async def get_ptz_info(self, camera: str) -> dict[str, Any]:
        return await self._request("GET", f"/api/{camera}/ptz/info")

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

    async def get_recording_days(
        self, *, cameras: str | None = None, timezone: str | None = None
    ) -> dict[str, bool]:
        params: dict[str, Any] = {}
        if cameras:
            params["cameras"] = cameras
        if timezone:
            params["timezone"] = timezone
        return await self._request("GET", "/api/recordings/summary", params=params)

    # ------------------------------------------------------------------ #
    # Exports
    # ------------------------------------------------------------------ #

    async def get_exports(
        self,
        *,
        export_case_id: str | None = None,
        cameras: str | None = None,
        start_date: float | None = None,
        end_date: float | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {}
        for key, val in {
            "export_case_id": export_case_id,
            "cameras": cameras,
            "start_date": start_date,
            "end_date": end_date,
        }.items():
            if val is not None:
                params[key] = val
        return await self._request("GET", "/api/exports", params=params)

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
        chapters: str | None = None,
        export_case_id: str | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {}
        if chapters is not None:
            body["chapters"] = chapters
        if export_case_id is not None:
            body["export_case_id"] = export_case_id
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
        # 0.18 removed DELETE /export/{id} in favour of bulk POST /exports/delete.
        if await self.version_tuple() >= (0, 18):
            return await self.delete_exports([export_id])
        return await self._request("DELETE", f"/api/export/{export_id}")

    # ---- Frigate 0.18+ export endpoints ----

    async def delete_exports(self, export_ids: list[str]) -> dict[str, Any]:
        return await self._request(
            "POST", "/api/exports/delete", json_body={"ids": export_ids}
        )

    async def reassign_exports(
        self, export_ids: list[str], export_case_id: str | None
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/api/exports/reassign",
            json_body={"ids": export_ids, "export_case_id": export_case_id},
        )

    async def create_exports_batch(
        self,
        items: list[dict[str, Any]],
        *,
        export_case_id: str | None = None,
        new_case_name: str | None = None,
        new_case_description: str | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"items": items}
        for key, val in {
            "export_case_id": export_case_id,
            "new_case_name": new_case_name,
            "new_case_description": new_case_description,
        }.items():
            if val is not None:
                body[key] = val
        return await self._request("POST", "/api/exports/batch", json_body=body)

    async def create_custom_export(
        self,
        camera: str,
        start: float,
        end: float,
        *,
        name: str | None = None,
        source: str | None = None,
        ffmpeg_input_args: str | None = None,
        ffmpeg_output_args: str | None = None,
        cpu_fallback: bool | None = None,
        export_case_id: str | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {}
        for key, val in {
            "name": name,
            "source": source,
            "ffmpeg_input_args": ffmpeg_input_args,
            "ffmpeg_output_args": ffmpeg_output_args,
            "cpu_fallback": cpu_fallback,
            "export_case_id": export_case_id,
        }.items():
            if val is not None:
                body[key] = val
        return await self._request(
            "POST",
            f"/api/export/custom/{camera}/start/{start}/end/{end}",
            json_body=body,
        )

    async def get_export_cases(self) -> list[dict[str, Any]]:
        return await self._request("GET", "/api/cases")

    async def get_export_case(self, case_id: str) -> dict[str, Any]:
        return await self._request("GET", f"/api/cases/{case_id}")

    async def create_export_case(
        self, name: str, *, description: str | None = None
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"name": name}
        if description is not None:
            body["description"] = description
        return await self._request("POST", "/api/cases", json_body=body)

    async def update_export_case(
        self,
        case_id: str,
        *,
        name: str | None = None,
        description: str | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {}
        if name is not None:
            body["name"] = name
        if description is not None:
            body["description"] = description
        return await self._request("PATCH", f"/api/cases/{case_id}", json_body=body)

    async def delete_export_case(
        self, case_id: str, *, delete_exports: bool = False
    ) -> dict[str, Any]:
        return await self._request(
            "DELETE",
            f"/api/cases/{case_id}",
            params={"delete_exports": delete_exports},
        )

    async def rename_export(
        self, export_id: str, name: str
    ) -> dict[str, Any]:
        return await self._request(
            "PATCH",
            f"/api/export/{export_id}/rename",
            json_body={"name": name},
        )

    # ------------------------------------------------------------------ #
    # Frigate 0.18+: camera features, profiles, VLM monitor, recordings delete
    # ------------------------------------------------------------------ #

    async def set_camera_feature(
        self,
        camera: str,
        feature: str,
        value: str,
        *,
        sub_command: str | None = None,
    ) -> dict[str, Any]:
        path = f"/api/camera/{camera}/set/{feature}"
        if sub_command is not None:
            path += f"/{sub_command}"
        return await self._request("PUT", path, json_body={"value": value})

    async def get_profiles(self) -> dict[str, Any]:
        return await self._request("GET", "/api/profiles")

    async def get_active_profile(self) -> dict[str, Any]:
        return await self._request("GET", "/api/profile/active")

    async def get_audio_labels(self) -> list[str]:
        return await self._request("GET", "/api/audio_labels")

    async def start_vlm_monitor(
        self,
        camera: str,
        condition: str,
        *,
        max_duration_minutes: int | None = None,
        labels: list[str] | None = None,
        zones: list[str] | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"camera": camera, "condition": condition}
        if max_duration_minutes is not None:
            body["max_duration_minutes"] = max_duration_minutes
        if labels is not None:
            body["labels"] = labels
        if zones is not None:
            body["zones"] = zones
        return await self._request("POST", "/api/vlm/monitor", json_body=body)

    async def get_vlm_monitor(self) -> dict[str, Any]:
        return await self._request("GET", "/api/vlm/monitor")

    async def cancel_vlm_monitor(self) -> dict[str, Any]:
        return await self._request("DELETE", "/api/vlm/monitor")

    async def delete_recordings(
        self,
        start: float,
        end: float,
        *,
        cameras: str | None = None,
        keep: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if cameras is not None:
            params["cameras"] = cameras
        if keep is not None:
            params["keep"] = keep
        return await self._request(
            "DELETE", f"/api/recordings/start/{start}/end/{end}", params=params
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

    # ------------------------------------------------------------------ #
    # Semantic search / audio
    # ------------------------------------------------------------------ #

    async def transcribe_event_audio(self, event_id: str) -> dict[str, Any]:
        return await self._request(
            "PUT", "/api/audio/transcribe", json_body={"event_id": event_id}
        )

    async def reindex_embeddings(self) -> dict[str, Any]:
        return await self._request("PUT", "/api/reindex")
