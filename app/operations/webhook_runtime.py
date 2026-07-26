from __future__ import annotations

import asyncio
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import AsyncIterator

from fastapi import HTTPException, Request, status


@dataclass(slots=True)
class WebhookRuntime:
    max_body_bytes: int
    max_concurrency: int
    active: int = field(default=0, init=False)
    _semaphore: asyncio.Semaphore = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if not 1 <= self.max_concurrency <= 100:
            raise ValueError("Webhook concurrency must be between 1 and 100")
        if not 1024 <= self.max_body_bytes <= 1_048_576:
            raise ValueError("Webhook body limit is outside the supported range")
        self._semaphore = asyncio.Semaphore(self.max_concurrency)

    @asynccontextmanager
    async def handle_slot(self, metrics=None) -> AsyncIterator[None]:
        started = time.perf_counter()
        await self._semaphore.acquire()
        waited = time.perf_counter() - started
        self.active += 1
        if metrics is not None:
            metrics.webhook_queue_wait.observe(waited)
            metrics.webhook_active.inc()
        try:
            yield
        finally:
            self.active -= 1
            self._semaphore.release()
            if metrics is not None:
                metrics.webhook_active.dec()

    async def read_body(self, request: Request) -> bytes:
        declared = request.headers.get("content-length")
        if declared:
            try:
                declared_size = int(declared)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid Content-Length header",
                ) from None
            if declared_size < 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid Content-Length header",
                )
            if declared_size > self.max_body_bytes:
                raise HTTPException(
                    status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                    detail="Webhook payload is too large",
                )
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > self.max_body_bytes:
                raise HTTPException(
                    status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                    detail="Webhook payload is too large",
                )
        return bytes(body)
