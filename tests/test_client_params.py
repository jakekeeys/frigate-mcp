"""Wire-level checks against Frigate v0.17.2 query/body typing.

Run: python tests/test_client_params.py   (pytest-compatible too)
"""

from __future__ import annotations

import asyncio
import json
import os

import httpx

os.environ.setdefault("FRIGATE_URL", "http://frigate.test")

from frigate_mcp.client.rest_client import FrigateClient  # noqa: E402


def _client(seen: list[httpx.Request], version: str = "0.17.2-3d4dd3a") -> FrigateClient:
    def handler(req: httpx.Request) -> httpx.Response:
        seen.append(req)
        if req.url.path == "/api/version":
            return httpx.Response(200, content=version.encode(), headers={"content-type": "text/plain"})
        if req.url.path.startswith("/api/logs/"):
            return httpx.Response(200, json={"totalLines": 1, "lines": ["x"]})
        if req.url.path.endswith((".jpg", ".gif", ".webp")):
            return httpx.Response(200, content=b"\xff\xd8")
        if req.url.path == "/api/config/raw":
            return httpx.Response(200, content=b'"mqtt:\\n  host: x"',
                                  headers={"content-type": "text/plain"})
        return httpx.Response(200, json=[])

    c = FrigateClient()
    c._client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url=c.base_url
    )
    return c


async def _run() -> None:
    seen: list[httpx.Request] = []
    c = _client(seen)

    # Frigate types these Optional[int]; a raw bool serialises as "true" -> 422.
    await c.get_events(has_clip=True, favorites=False, in_progress=None)
    q = dict(seen[-1].url.params)
    assert q == {"has_clip": "1", "favorites": "0"}, q

    await c.get_event_summary(has_clip=True)
    assert dict(seen[-1].url.params) == {"has_clip": "1"}

    # latest.jpg takes `height`, best.jpg takes nothing.
    await c.get_latest_frame("cam", height=240)
    assert dict(seen[-1].url.params) == {"height": "240"}
    await c.get_camera_label_best("cam", "person")
    assert not seen[-1].url.query

    # EventsEndBody is a required body upstream.
    await c.end_event("abc")
    assert seen[-1].method == "PUT"
    assert json.loads(seen[-1].content) == {"end_time": None}

    # logs is JSON, not text.
    logs = await c.get_logs("frigate", start=0, end=10)
    assert logs == {"totalLines": 1, "lines": ["x"]}
    assert dict(seen[-1].url.params) == {"start": "0", "end": "10"}

    # DELETE /events/ carries a JSON body.
    await c.delete_events(["a", "b"])
    assert seen[-1].method == "DELETE"
    assert json.loads(seen[-1].content) == {"event_ids": ["a", "b"]}

    # create trigger: camera/name are query params, type/data/threshold body.
    await c.create_trigger_embedding("cam", "pkg", trigger_type="description", data="a parcel", threshold=0.6)
    assert dict(seen[-1].url.params) == {"camera_name": "cam", "name": "pkg"}
    assert json.loads(seen[-1].content) == {"type": "description", "data": "a parcel", "threshold": 0.6}

    # config/raw is a JSON-encoded string served as text/plain.
    assert await c.get_config_raw() == "mqtt:\n  host: x"

    await c.set_config({"mqtt": {"host": "y"}}, requires_restart=False)
    assert json.loads(seen[-1].content) == {"config_data": {"mqtt": {"host": "y"}}, "requires_restart": 0}

    await c.get_recording_snapshot("cam", 1.5, fmt="png", height=100)
    assert seen[-1].url.path == "/api/cam/recordings/1.5/snapshot.png"
    assert dict(seen[-1].url.params) == {"height": "100"}

    # get_snapshot: bool flags are ints, extra params pass through.
    await c.get_snapshot("e1", crop=True, height=200, bbox=False)
    assert dict(seen[-1].url.params) == {"crop": "1", "height": "200", "bbox": "0"}

    # set_camera_feature: path + sub_command + body.
    await c.set_camera_feature("cam", "zone", "OFF", sub_command="drive")
    assert seen[-1].url.path == "/api/camera/cam/set/zone/drive"
    assert json.loads(seen[-1].content) == {"value": "OFF"}

    await c.delete_recordings(10, 20, cameras="a,b")
    assert seen[-1].method == "DELETE" and seen[-1].url.path == "/api/recordings/start/10/end/20"
    assert dict(seen[-1].url.params) == {"cameras": "a,b"}

    # delete_export is version-gated: 0.17 -> DELETE /export/{id}
    await c.delete_export("x1")
    assert seen[-1].method == "DELETE" and seen[-1].url.path == "/api/export/x1"
    await c.close()

    seen18: list[httpx.Request] = []
    c18 = _client(seen18, version="0.18.0-rc1-abc123")
    await c18.delete_export("x1")
    assert seen18[-1].method == "POST" and seen18[-1].url.path == "/api/exports/delete"
    assert json.loads(seen18[-1].content) == {"ids": ["x1"]}
    await c18.delete_export("x2")  # version cached: exactly one /api/version call
    assert sum(r.url.path == "/api/version" for r in seen18) == 1
    await c18.close()


def test_client_params() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    test_client_params()
    print("ok")
