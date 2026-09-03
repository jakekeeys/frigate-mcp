"""Contract tests for the Frigate 0.18 HTTP client."""

from __future__ import annotations

import asyncio
import json
from urllib.parse import parse_qs

import httpx

from frigate_mcp.client.rest_client import FrigateClient


def call(coro):
    return asyncio.run(coro)


def client_for(handler, requests):
    async def record(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return await handler(request)

    client = FrigateClient(base_url="http://frigate.test")
    client._client = httpx.AsyncClient(
        transport=httpx.MockTransport(record),
        base_url=client.base_url,
        headers={"Content-Type": "application/json"},
    )
    return client


def test_event_flags_use_integer_query_values():
    requests = []

    async def handler(_request):
        return httpx.Response(200, json=[])

    client = client_for(handler, requests)
    try:
        call(
            client.get_events(
                has_clip=True,
                has_snapshot=False,
                in_progress=True,
                favorites=False,
                include_thumbnails=True,
            )
        )
        query = parse_qs(requests[0].url.query.decode())
        assert query["has_clip"] == ["1"]
        assert query["has_snapshot"] == ["0"]
        assert query["in_progress"] == ["1"]
        assert query["favorites"] == ["0"]
        assert query["include_thumbnails"] == ["1"]
    finally:
        call(client.close())


def test_event_summary_flags_use_integer_query_values():
    requests = []

    async def handler(_request):
        return httpx.Response(200, json=[])

    client = client_for(handler, requests)
    try:
        call(client.get_event_summary(has_clip=True, has_snapshot=False))
        query = parse_qs(requests[0].url.query.decode())
        assert query["has_clip"] == ["1"]
        assert query["has_snapshot"] == ["0"]
    finally:
        call(client.close())


def test_end_event_sends_required_empty_body():
    requests = []

    async def handler(_request):
        return httpx.Response(200, json={"success": True})

    client = client_for(handler, requests)
    try:
        assert call(client.end_event("event-1")) == {"success": True}
        request = requests[0]
        assert request.method == "PUT"
        assert request.url.path == "/api/events/event-1/end"
        assert json.loads(request.content) == {}
    finally:
        call(client.close())


def test_delete_export_uses_018_bulk_endpoint():
    requests = []

    async def handler(_request):
        return httpx.Response(200, json={"success": True})

    client = client_for(handler, requests)
    try:
        call(client.delete_export("export-1"))
        request = requests[0]
        assert request.method == "POST"
        assert request.url.path == "/api/exports/delete"
        assert json.loads(request.content) == {"ids": ["export-1"]}
    finally:
        call(client.close())


def test_create_export_uses_018_body_fields():
    requests = []

    async def handler(_request):
        return httpx.Response(202, json={"success": True, "export_id": "export-1"})

    client = client_for(handler, requests)
    try:
        call(
            client.create_export(
                "front_door",
                100.0,
                110.0,
                source="recordings",
                name="test",
                export_case_id="case-1",
                chapters="review_items",
            )
        )
        body = json.loads(requests[0].content)
        assert body == {
            "source": "recordings",
            "name": "test",
            "export_case_id": "case-1",
            "chapters": "review_items",
        }
        assert "playback" not in body
    finally:
        call(client.close())


def test_clean_snapshot_uses_webp_endpoint():
    requests = []

    async def handler(_request):
        return httpx.Response(200, content=b"webp")

    client = client_for(handler, requests)
    try:
        assert call(client.get_clean_snapshot("event-1")) == b"webp"
        request = requests[0]
        assert request.method == "GET"
        assert request.url.path == "/api/events/event-1/snapshot-clean.webp"
    finally:
        call(client.close())
