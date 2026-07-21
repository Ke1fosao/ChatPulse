from aiogram import Router
from aiogram.types import MessageReactionCountUpdated, MessageReactionUpdated

from app.repositories.activity import ActivityRepository

router = Router(name="reactions")


def reaction_key(reaction: object) -> str:
    emoji = getattr(reaction, "emoji", None)
    if emoji:
        return str(emoji)
    custom_emoji_id = getattr(reaction, "custom_emoji_id", None)
    if custom_emoji_id:
        return f"custom:{custom_emoji_id}"
    return "⭐"


@router.message_reaction()
async def reaction_changed(
    event: MessageReactionUpdated,
    repository: ActivityRepository,
) -> None:
    await repository.record_reaction(
        chat_id=event.chat.id,
        message_id=event.message_id,
        old_reactions=[reaction_key(item) for item in event.old_reaction],
        new_reactions=[reaction_key(item) for item in event.new_reaction],
        occurred_at=event.date,
    )


@router.message_reaction_count()
async def reaction_count_changed(
    event: MessageReactionCountUpdated,
    repository: ActivityRepository,
) -> None:
    await repository.record_reaction_count(
        chat_id=event.chat.id,
        message_id=event.message_id,
        reaction_counts={reaction_key(item.type): item.total_count for item in event.reactions},
        occurred_at=event.date,
    )
