# ChatPulse observability

## Correlation and logs

Every HTTP response contains `X-Request-ID`. Valid incoming IDs match `[A-Za-z0-9._-]{8,128}`; other values are replaced. Production logs are JSON and include event, request ID, route template, method, status, duration, application version, environment, build SHA, and Cloud Run revision when configured.

Never log authorization headers, cookies, Telegram init data, raw webhook bodies, payment payloads, secrets, message text, captions, files, or private notes.

## Protected metrics

Enable with `METRICS_ENABLED=true` and configure `INTERNAL_METRICS_TOKEN`. Scrape `/internal/metrics` with `Authorization: Bearer <token>`.

Required metric families begin with `chatpulse_` and cover HTTP, webhook outcomes/queueing, Redis, rate limits, leases, database slow queries, scheduler jobs, and stable API errors. Labels are bounded and never contain Telegram IDs, request IDs, usernames, invoice IDs, or parameterized URLs.

## Initial SLOs

- `/health` and authenticated core API availability: 99.9% monthly.
- Server error rate: below 1% over 15 minutes.
- Cached Mini App read p95: below 750 ms.
- Group-list read p95: below 1.5 s.
- Webhook handler p95 excluding Telegram retries: below 2 s.
- Duplicate singleton scheduler executions: zero.

## Initial alerts

- readiness unavailable for 2 consecutive minutes;
- 5xx rate above 1% for 15 minutes, critical above 2% for 5 minutes;
- webhook failed/retry trend increasing for 5 minutes;
- Redis failure counter increasing while billing/owner/scheduler traffic exists;
- database slow-query counter or pool wait rising above baseline;
- scheduler `skipped` unexpectedly repeated for the same job window;
- no successful weekly scheduler execution in the expected window.

## Sentry

Sentry is optional and controlled by `SENTRY_DSN`. Expected validation/auth/rate-limit/permission errors are not reported. Request bodies, cookies, query strings, user objects, Telegram payloads, and configured secrets are removed before events leave the process.
