from __future__ import annotations

import itertools
import os
import random

from locust import HttpUser, between, task

from load.identity import signed_init_data

_UPDATE_IDS = itertools.count(8_000_000)


class ChatPulseUser(HttpUser):
    wait_time = between(0.2, 1.2)

    def on_start(self) -> None:
        token = os.environ["LOAD_BOT_TOKEN"]
        user_id = int(os.getenv("LOAD_USER_ID", "900000001")) + random.randint(0, 1000)
        self.headers = {"X-Telegram-Init-Data": signed_init_data(token, user_id)}
        self.group_id = os.getenv("LOAD_GROUP_ID")
        self.webhook_path = os.getenv("LOAD_WEBHOOK_PATH")
        self.webhook_secret = os.getenv("LOAD_WEBHOOK_SECRET")
        self.enable_owner = os.getenv("LOAD_OWNER_SCENARIOS") == "1"
        self.enable_invoice = os.getenv("LOAD_INVOICE_SCENARIO") == "1"

    @task(8)
    def home(self) -> None:
        self.client.get("/api/miniapp/v1/home", headers=self.headers, name="GET /home")

    @task(6)
    def groups(self) -> None:
        self.client.get("/api/miniapp/v1/groups-v2", headers=self.headers, name="GET /groups")

    @task(4)
    def achievements(self) -> None:
        self.client.get(
            "/api/miniapp/v1/achievements",
            headers=self.headers,
            name="GET /achievements",
        )

    @task(3)
    def group_reads(self) -> None:
        if not self.group_id:
            return
        endpoint = random.choice(("overview", "ranking", "analytics", "awards"))
        self.client.get(
            f"/api/miniapp/v1/groups/{self.group_id}/{endpoint}",
            headers=self.headers,
            name=f"GET /groups/:id/{endpoint}",
        )

    @task(1)
    def favorite_write(self) -> None:
        if not self.group_id:
            return
        self.client.put(
            f"/api/miniapp/v1/groups/{self.group_id}/favorite",
            headers=self.headers,
            json={"is_favorite": bool(random.getrandbits(1))},
            name="PUT /groups/:id/favorite",
        )

    @task(1)
    def owner_search(self) -> None:
        if not self.enable_owner:
            return
        self.client.get(
            "/api/owner/v1/users?limit=20",
            headers=self.headers,
            name="GET /owner/users",
        )

    @task(1)
    def invoice_rate_limit(self) -> None:
        if not self.enable_invoice:
            return
        with self.client.post(
            "/api/miniapp/v1/vip/invoice",
            headers=self.headers,
            json={"plan_code": "monthly_30d"},
            name="POST /vip/invoice",
            catch_response=True,
        ) as response:
            if response.status_code in {200, 409, 429}:
                response.success()

    @task(1)
    def webhook_burst(self) -> None:
        if not self.webhook_path or not self.webhook_secret:
            return
        update_id = next(_UPDATE_IDS)
        headers = {"X-Telegram-Bot-Api-Secret-Token": self.webhook_secret}
        payload = {"update_id": update_id}
        self.client.post(
            self.webhook_path,
            headers=headers,
            json=payload,
            name="POST /telegram/webhook",
        )
        self.client.post(
            self.webhook_path,
            headers=headers,
            json=payload,
            name="POST /telegram/webhook duplicate",
        )

    @task(1)
    def health(self) -> None:
        self.client.get("/health", name="GET /health")
