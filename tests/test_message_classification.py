from datetime import UTC, datetime

from aiogram.types import Message

from app.bot.routers.groups import classify_message
from app.domain import MessageActivity


def make_message(**overrides) -> Message:
    payload = {
        "message_id": 1,
        "date": datetime(2026, 7, 21, 18, 0, tzinfo=UTC),
        "chat": {"id": -1001, "type": "supergroup", "title": "Test"},
        "from": {"id": 101, "is_bot": False, "first_name": "Dmytro"},
        "text": "Hello",
    }
    payload.update(overrides)
    return Message.model_validate(payload)


def test_commands_are_not_counted() -> None:
    assert classify_message(make_message(text="/stats")) is None


def test_messages_from_bots_are_not_counted() -> None:
    message = make_message(
        **{"from": {"id": 202, "is_bot": True, "first_name": "Other bot"}}
    )
    assert classify_message(message) is None


def test_media_reply_is_classified() -> None:
    message = make_message(
        text=None,
        photo=[
            {
                "file_id": "photo-id",
                "file_unique_id": "unique-photo-id",
                "width": 100,
                "height": 100,
            }
        ],
        reply_to_message={
            "message_id": 2,
            "date": datetime(2026, 7, 21, 17, 59, tzinfo=UTC),
            "chat": {"id": -1001, "type": "supergroup", "title": "Test"},
            "from": {"id": 303, "is_bot": False, "first_name": "Vika"},
            "text": "Previous",
        },
    )

    assert classify_message(message) == MessageActivity(
        is_media=True,
        is_reply=True,
        is_photo=True,
    )


def test_regular_message_is_classified() -> None:
    assert classify_message(make_message()) == MessageActivity(
        is_media=False, is_reply=False
    )
