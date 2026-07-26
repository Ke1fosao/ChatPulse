from __future__ import annotations

import asyncio

import pytest
from fastapi import HTTPException

from app.operations.webhook_runtime import WebhookRuntime


class FakeRequest:
    def __init__(self, chunks: list[bytes], content_length: str | None = None) -> None:
        self.headers = {} if content_length is None else {"content-length": content_length}
        self._chunks = chunks

    async def stream(self):
        for chunk in self._chunks:
            yield chunk


async def test_body_limit_rejects_declared_oversize_before_streaming() -> None:
    runtime = WebhookRuntime(max_body_bytes=1024, max_concurrency=2)
    with pytest.raises(HTTPException) as caught:
        await runtime.read_body(FakeRequest([], "1025"))  # type: ignore[arg-type]
    assert caught.value.status_code == 413


async def test_body_limit_rejects_chunked_oversize() -> None:
    runtime = WebhookRuntime(max_body_bytes=1024, max_concurrency=2)
    with pytest.raises(HTTPException) as caught:
        await runtime.read_body(FakeRequest([b"a" * 700, b"b" * 400]))  # type: ignore[arg-type]
    assert caught.value.status_code == 413


async def test_concurrency_slot_is_released_after_error() -> None:
    runtime = WebhookRuntime(max_body_bytes=1024, max_concurrency=1)
    entered = asyncio.Event()
    release = asyncio.Event()

    async def first() -> None:
        with pytest.raises(RuntimeError):
            async with runtime.handle_slot():
                entered.set()
                await release.wait()
                raise RuntimeError("boom")

    async def second() -> None:
        await entered.wait()
        async with runtime.handle_slot():
            assert runtime.active == 1

    first_task = asyncio.create_task(first())
    second_task = asyncio.create_task(second())
    await entered.wait()
    assert runtime.active == 1
    release.set()
    await asyncio.gather(first_task, second_task)
    assert runtime.active == 0
