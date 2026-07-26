# Load testing

## Local correctness smoke

```bash
pip install -e ".[dev]" -c requirements.lock
python -m scripts.load_smoke
locust -f load/locustfile.py --list
```

The local smoke uses an isolated SQLite database and verifies concurrent liveness/readiness traffic with zero unexpected failures.

## Staging profile

Use the manual `Staging load profile` workflow with protected staging secrets:

- `LOAD_BOT_TOKEN` — staging bot only;
- `LOAD_USER_ID` — seeded test user range;
- `LOAD_HOST` — staging service URL.

Default profile: 20 users for 15 minutes. Reports contain aggregate timings only and must not contain init data, Telegram payloads, customer data, or secrets.

Acceptance:

- error rate below 1%;
- no duplicate webhook side effects;
- no payment, XP, or achievement invariant failure;
- p95 within the endpoint-class SLO;
- no unbounded process memory or database/Redis connection growth.
