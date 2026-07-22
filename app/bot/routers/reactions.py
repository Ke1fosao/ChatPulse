from aiogram import Bot, Router
from aiogram.types import MessageReactionCountUpdated, MessageReactionUpdated

from app.repositories.activity import ActivityRepository
from app.repositories.gamification import GamificationRepository
from app.services.gamification import format_gamification_announcement

router = Router(name="reactions")


def reaction_key(reaction: object) -> str:
    emoji = getattr(reaction, "emoji", None)
    if emoji:
        return str(emoji)
    custom_emoji_id = getattr(reaction, "custom_emoji_id", None)
    if custom_emoji_id:
        return f"custom:{custom_emoji_id}"
    return "⭐"


async def _announce_update(
    bot: Bot,
    event: MessageReactionUpdated | MessageReactionCountUpdated,
    gamification_repository: GamificationRepository,
    positive_delta: int,
) -> None:
    if positive_delta <= 0:
        return
    update = await gamification_repository.award_reaction_xp(
        chat_id=event.chat.id,
        message_id=event.message_id,
        positive_delta=positive_delta,
        occurred_at=event.date,
    )
    display_name = await gamification_repository.get_message_author_name(
        event.chat.id,
        event.message_id,
    )
    announcement = format_gamification_announcement(display_name or "Учасник", update)
    if announcement:
        await bot.send_message(event.chat.id, announcement)


@router.message_reaction()
async def reaction_changed(
    event: MessageReactionUpdated,
    bot: Bot,
    repository: ActivityRepository,
    gamification_repository: GamificationRepository,
) -> None:
    old_reactions = [reaction_key(item) for item in event.old_reaction]
    new_reactions = [reaction_key(item) for item in event.new_reaction]
    tracked = await repository.record_reaction(
        chat_id=event.chat.id,
        message_id=event.message_id,
        old_reactions=old_reactions,
        new_reactions=new_reactions,
        occurred_at=event.date,
    )
    if not tracked:
        return
    previous, current = await gamification_repository.update_message_reaction_total(
        event.chat.id,
        event.message_id,
        delta=len(new_reactions) - len(old_reactions),
    )
    await _announce_update(bot, event, gamification_repository, current - previous)


@router.message_reaction_count()
async def reaction_count_changed(
    event: MessageReactionCountUpdated,
    bot: Bot,
    repository: ActivityRepository,
    gamification_repository: GamificationRepository,
) -> None:
    reaction_counts = {reaction_key(item.type): item.total_count for item in event.reactions}
    tracked = await repository.record_reaction_count(
        chat_id=event.chat.id,
        message_id=event.message_id,
        reaction_counts=reaction_counts,
        occurred_at=event.date,
    )
    if not tracked:
        return
    previous, current = await gamification_repository.update_message_reaction_total(
        event.chat.id,
        event.message_id,
        total=sum(reaction_counts.values()),
    )
    await _announce_update(bot, event, gamification_repository, current - previous)
