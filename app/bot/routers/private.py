from aiogram import Bot, F, Router
from aiogram.enums import ChatType
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from app.bot.keyboards import open_miniapp_keyboard, private_start_keyboard
from app.domain import UserData
from app.repositories.activity import ActivityRepository
from app.repositories.engagement import EngagementRepository
from app.repositories.miniapp import MiniAppRepository
from app.repositories.owner import OwnerClaimResult, OwnerRepository

router = Router(name="private")


def _user_data(message: Message) -> UserData | None:
    user = message.from_user
    if user is None:
        return None
    return UserData(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        language_code=user.language_code,
    )


def _onboarding_text(onboarding: dict) -> str:
    if onboarding["is_complete"]:
        return (
            "✅ <b>Налаштування завершено</b>\n"
            "ChatPulse уже збирає статистику, XP, серії та досягнення."
        )
    lines = [
        f"🚀 <b>Швидкий старт — {onboarding['completed_steps']}/3</b>",
        "",
    ]
    for index, step in enumerate(onboarding["steps"], start=1):
        icon = "✅" if step["completed"] else "○"
        lines.append(f"{icon} <b>{index}. {step['title']}</b>")
        if not step["completed"]:
            lines.append(f"   {step['description']}")
    return "\n".join(lines)


@router.message(CommandStart(), F.chat.type == ChatType.PRIVATE)
async def start_command(
    message: Message,
    bot: Bot,
    repository: ActivityRepository,
    engagement_repository: EngagementRepository,
    miniapp_url: str | None = None,
) -> None:
    user = _user_data(message)
    if user is None:
        return
    await repository.upsert_user(user)
    await engagement_repository.mark_private_started(user.telegram_id, now=message.date)
    bot_info = await bot.get_me()
    bot_username = bot_info.username or "ChatPulseBot"
    onboarding = await engagement_repository.get_onboarding(
        user.telegram_id,
        bot_username=bot_username,
        now=message.date,
    )
    await message.answer(
        "⚡ <b>ChatPulse</b> перетворює активність у групах на красиву аналітику, "
        "XP, рівні, серії та досягнення.\n\n"
        f"{_onboarding_text(onboarding)}\n\n"
        "Відкрий Mini App, щоб бачити прогрес у реальному часі. "
        "Тексти повідомлень і файли не зберігаються.",
        reply_markup=private_start_keyboard(bot_username, miniapp_url),
        parse_mode="HTML",
    )


@router.message(Command("claimadmin"), F.chat.type == ChatType.PRIVATE)
async def claim_admin_command(
    message: Message,
    owner_repository: OwnerRepository,
) -> None:
    user = message.from_user
    if user is None:
        return

    result = await owner_repository.claim_owner(user.id, user.username)
    responses = {
        OwnerClaimResult.CLAIMED: (
            "✅ Акаунт @veheblya закріплено як власника ChatPulse.\n\n"
            "Надалі права перевіряються за незмінним Telegram ID, тому зміна username "
            "не забере доступ."
        ),
        OwnerClaimResult.ALREADY_OWNER: "👑 Цей акаунт вже є власником ChatPulse.",
        OwnerClaimResult.USERNAME_MISMATCH: ("⛔ Команда доступна лише акаунту @veheblya."),
        OwnerClaimResult.CLAIMED_BY_OTHER: (
            "⛔ Власник ChatPulse вже закріплений. Повторне призначення заблоковано."
        ),
    }
    await message.answer(responses[result])


@router.message(Command("open"), F.chat.type == ChatType.PRIVATE)
async def open_command(message: Message, miniapp_url: str | None = None) -> None:
    if not miniapp_url:
        await message.answer("Mini App ще не підключено до публічного домену.")
        return
    await message.answer(
        "⚡ Твій особистий ChatPulse готовий:",
        reply_markup=open_miniapp_keyboard(miniapp_url),
    )


@router.message(Command("profile"), F.chat.type == ChatType.PRIVATE)
async def private_profile_command(
    message: Message,
    miniapp_repository: MiniAppRepository,
    miniapp_url: str | None = None,
) -> None:
    if message.from_user is None:
        return
    profile = await miniapp_repository.get_private_summary(message.from_user.id)
    if profile is None:
        await message.answer("Профіль ще порожній. Додай ChatPulse до групи й прояви активність.")
        return
    progress = profile["global_progress"]
    stats = profile["quick_stats"]
    text = (
        f"👤 <b>{profile['display_name']}</b>\n\n"
        f"⚡ Загальний рівень {progress['level']} · {progress['tier']}\n"
        f"✨ {progress['xp_total']} XP · глобальне місце #{progress['rank']}\n"
        f"🔥 Серія: {stats['current_streak']} днів\n"
        f"👥 Груп: {stats['groups_count']}"
    )
    markup = open_miniapp_keyboard(miniapp_url) if miniapp_url else None
    await message.answer(text, reply_markup=markup, parse_mode="HTML")


@router.message(Command("groups"), F.chat.type == ChatType.PRIVATE)
async def private_groups_command(
    message: Message,
    miniapp_repository: MiniAppRepository,
    miniapp_url: str | None = None,
) -> None:
    if message.from_user is None:
        return
    groups = await miniapp_repository.list_groups(message.from_user.id)
    if not groups:
        await message.answer("У профілі ще немає груп. Додай ChatPulse до групового чату.")
        return
    lines = ["👥 <b>Твої групи</b>", ""]
    for group in groups[:8]:
        lines.append(
            f"• {group['title']} — рівень {group['level']}, "
            f"{group['period']['xp_earned']} XP за 7 днів"
        )
    markup = open_miniapp_keyboard(miniapp_url) if miniapp_url else None
    await message.answer("\n".join(lines), reply_markup=markup, parse_mode="HTML")


@router.message(Command("achievements"), F.chat.type == ChatType.PRIVATE)
async def private_achievements_command(
    message: Message,
    miniapp_repository: MiniAppRepository,
    miniapp_url: str | None = None,
) -> None:
    if message.from_user is None:
        return
    achievements = await miniapp_repository.get_achievements(message.from_user.id)
    earned = [item for item in achievements or [] if item["earned"]]
    lines = [f"🏅 <b>Досягнення: {len(earned)} отримано</b>", ""]
    if earned:
        lines.extend(f"• {item['title']} — {item['description']}" for item in earned[:6])
    else:
        lines.append("Перша нагорода вже близько — набери 10 XP у будь-якій групі.")
    markup = open_miniapp_keyboard(miniapp_url) if miniapp_url else None
    await message.answer("\n".join(lines), reply_markup=markup, parse_mode="HTML")


@router.message(Command("help"), F.chat.type == ChatType.PRIVATE)
async def help_command(message: Message) -> None:
    await message.answer(
        "Команди ChatPulse:\n"
        "/open — відкрити Mini App\n"
        "/profile — короткий профіль\n"
        "/groups — мої групи\n"
        "/achievements — мої нагороди\n\n"
        "Додай бота до групи, признач адміністратором і вимкни Privacy Mode. "
        "ChatPulse не зберігає тексти повідомлень або файли."
    )
