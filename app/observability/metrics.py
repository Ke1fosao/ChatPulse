from __future__ import annotations

from dataclasses import dataclass

from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, generate_latest


@dataclass(slots=True)
class Metrics:
    registry: CollectorRegistry
    http_requests: Counter
    http_duration: Histogram
    webhook_events: Counter
    webhook_active: Gauge
    webhook_queue_wait: Histogram
    redis_failures: Counter
    redis_latency: Histogram
    rate_limits: Counter
    leases: Counter
    telegram_calls: Counter
    telegram_duration: Histogram
    telegram_cache: Counter
    database_checkout_wait: Histogram
    database_pool_active: Gauge
    database_slow_queries: Counter
    transaction_rollbacks: Counter
    scheduler_jobs: Counter
    api_errors: Counter

    @classmethod
    def create(cls) -> "Metrics":
        registry = CollectorRegistry(auto_describe=True)
        return cls(
            registry=registry,
            http_requests=Counter(
                "chatpulse_http_requests_total",
                "HTTP requests",
                ("route", "method", "status_class"),
                registry=registry,
            ),
            http_duration=Histogram(
                "chatpulse_http_request_duration_seconds",
                "HTTP request duration",
                ("route", "method"),
                registry=registry,
            ),
            webhook_events=Counter(
                "chatpulse_webhook_events_total",
                "Webhook outcomes",
                ("outcome",),
                registry=registry,
            ),
            webhook_active=Gauge(
                "chatpulse_webhook_active_handlers",
                "Active webhook handlers",
                registry=registry,
            ),
            webhook_queue_wait=Histogram(
                "chatpulse_webhook_queue_wait_seconds",
                "Webhook queue wait",
                registry=registry,
            ),
            redis_failures=Counter(
                "chatpulse_redis_failures_total",
                "Redis failures",
                ("operation",),
                registry=registry,
            ),
            redis_latency=Histogram(
                "chatpulse_redis_operation_duration_seconds",
                "Redis operation latency",
                ("operation",),
                registry=registry,
            ),
            rate_limits=Counter(
                "chatpulse_rate_limit_total",
                "Rate limit decisions",
                ("policy", "outcome"),
                registry=registry,
            ),
            leases=Counter(
                "chatpulse_lease_total",
                "Distributed lease outcomes",
                ("operation", "outcome"),
                registry=registry,
            ),
            telegram_calls=Counter(
                "chatpulse_telegram_api_calls_total",
                "Telegram API call outcomes",
                ("operation", "outcome"),
                registry=registry,
            ),
            telegram_duration=Histogram(
                "chatpulse_telegram_api_duration_seconds",
                "Telegram API call duration",
                ("operation",),
                registry=registry,
            ),
            telegram_cache=Counter(
                "chatpulse_telegram_cache_total",
                "Telegram access cache outcomes",
                ("outcome",),
                registry=registry,
            ),
            database_checkout_wait=Histogram(
                "chatpulse_database_checkout_wait_seconds",
                "Database connection pool checkout wait",
                registry=registry,
            ),
            database_pool_active=Gauge(
                "chatpulse_database_pool_active_connections",
                "Checked out database connections",
                registry=registry,
            ),
            database_slow_queries=Counter(
                "chatpulse_database_slow_queries_total",
                "Slow database queries",
                ("operation", "table"),
                registry=registry,
            ),
            transaction_rollbacks=Counter(
                "chatpulse_transaction_rollbacks_total",
                "Database transaction rollbacks",
                ("operation",),
                registry=registry,
            ),
            scheduler_jobs=Counter(
                "chatpulse_scheduler_jobs_total",
                "Scheduler outcomes",
                ("job", "outcome"),
                registry=registry,
            ),
            api_errors=Counter(
                "chatpulse_api_errors_total",
                "Stable API errors",
                ("code",),
                registry=registry,
            ),
        )

    def render(self) -> bytes:
        return generate_latest(self.registry)
