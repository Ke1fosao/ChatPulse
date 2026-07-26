import pytest
from pydantic import ValidationError

from app.api.miniapp.responses import HomeResponse
from app.config import Settings
from app.main import create_app


def build_settings() -> Settings:
    return Settings(
        bot_token="123456:test-token",
        webhook_path_secret="path-secret",
        webhook_header_secret="header-secret",
        scheduler_secret="scheduler-secret",
        database_url="sqlite+aiosqlite:///:memory:",
    )


def test_miniapp_json_operations_reference_response_schemas() -> None:
    schema = create_app(build_settings()).openapi()
    checked = [
        ("/api/miniapp/v1/home", "get"),
        ("/api/miniapp/v1/groups-v2", "get"),
        ("/api/miniapp/v1/groups/{chat_id}/overview", "get"),
        ("/api/miniapp/v1/groups/{chat_id}/ranking", "get"),
        ("/api/miniapp/v1/achievements", "get"),
        ("/api/miniapp/v1/onboarding", "get"),
    ]
    for path, method in checked:
        response_schema = schema["paths"][path][method]["responses"]["200"]["content"][
            "application/json"
        ]["schema"]
        assert "$ref" in response_schema


def test_response_models_reject_unknown_top_level_fields() -> None:
    with pytest.raises(ValidationError):
        HomeResponse.model_validate(
            {
                "user": {"telegram_id": 101},
                "account": {
                    "plan": "free",
                    "is_owner": False,
                    "is_vip": False,
                    "vip_expires_at": None,
                    "entitlements": [],
                },
                "groups": [],
                "unexpected": True,
            }
        )
