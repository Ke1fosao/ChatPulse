from __future__ import annotations

import logging
import re
import time
from typing import Any

from sqlalchemy import event
from sqlalchemy.pool import AsyncAdaptedQueuePool

from app.version import APP_VERSION

logger = logging.getLogger("chatpulse.database")
_TABLE_PATTERN = re.compile(
    r"\b(?:from|join|update|into|table)\s+[\"`]?([a-zA-Z_][a-zA-Z0-9_]*)",
    re.IGNORECASE,
)
_OPERATION_PATTERN = re.compile(r"^\s*([a-zA-Z]+)")


class InstrumentedAsyncQueuePool(AsyncAdaptedQueuePool):
    """Queue pool that records the full blocking checkout acquisition time."""

    chatpulse_metrics: Any = None

    def _do_get(self):
        started = time.perf_counter()
        try:
            return super()._do_get()
        finally:
            metrics = getattr(self, "chatpulse_metrics", None)
            if metrics is not None:
                metrics.database_checkout_wait.observe(time.perf_counter() - started)


def normalized_query_shape(statement: str) -> tuple[str, tuple[str, ...]]:
    operation_match = _OPERATION_PATTERN.search(statement)
    operation = operation_match.group(1).upper() if operation_match else "UNKNOWN"
    tables = tuple(sorted(set(_TABLE_PATTERN.findall(statement)))) or ("unknown",)
    return operation, tables


def install_query_instrumentation(engine, *, slow_query_ms: int, metrics=None) -> None:
    pool = engine.sync_engine.pool
    if hasattr(pool, "chatpulse_metrics"):
        pool.chatpulse_metrics = metrics

    @event.listens_for(engine.sync_engine, "before_cursor_execute")
    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        context._chatpulse_started = time.perf_counter()

    @event.listens_for(engine.sync_engine, "after_cursor_execute")
    def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        started = getattr(context, "_chatpulse_started", None)
        if started is None:
            return
        duration_ms = (time.perf_counter() - started) * 1000
        if duration_ms < slow_query_ms:
            return
        operation, tables = normalized_query_shape(statement)
        logger.warning(
            "database_slow_query operation=%s tables=%s duration_ms=%.2f",
            operation,
            ",".join(tables),
            duration_ms,
        )
        if metrics is not None:
            for table in tables:
                metrics.database_slow_queries.labels(operation=operation, table=table).inc()

    if metrics is not None:

        @event.listens_for(engine.sync_engine, "checkout")
        def checkout(dbapi_connection, connection_record, connection_proxy):
            metrics.database_pool_active.inc()

        @event.listens_for(engine.sync_engine, "checkin")
        def checkin(dbapi_connection, connection_record):
            metrics.database_pool_active.dec()

        @event.listens_for(engine.sync_engine, "rollback")
        def rollback(connection):
            metrics.transaction_rollbacks.labels(operation="transaction").inc()


def postgresql_engine_options(settings: Any) -> dict[str, Any]:
    server_settings = {
        "application_name": f"chatpulse/{APP_VERSION}",
        "statement_timeout": str(settings.db_statement_timeout_ms),
    }
    connect_args: dict[str, Any] = {"server_settings": server_settings}
    if settings.db_disable_prepared_statements:
        connect_args["statement_cache_size"] = 0
        connect_args["prepared_statement_cache_size"] = 0
    return {
        "poolclass": InstrumentedAsyncQueuePool,
        "pool_pre_ping": True,
        "pool_size": settings.db_pool_size,
        "max_overflow": settings.db_max_overflow,
        "pool_timeout": settings.db_pool_timeout_seconds,
        "pool_recycle": settings.db_pool_recycle_seconds,
        "connect_args": connect_args,
    }
