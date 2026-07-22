from io import BytesIO
from typing import Any

from PIL import Image, ImageDraw

from app.services.report_cards import FONT_BOLD_PATHS, FONT_REGULAR_PATHS, _font

CARD_SIZE = (1200, 1200)


def _fit(value: str, limit: int) -> str:
    cleaned = " ".join(value.split())
    return cleaned if len(cleaned) <= limit else cleaned[: limit - 1].rstrip() + "…"


def _account_style(account: dict[str, Any]) -> tuple[str, str, tuple[int, int, int]]:
    if account.get("is_owner"):
        return "CREATOR", "OWNER ACCESS", (245, 200, 107)
    if account.get("is_vip"):
        return "VIP CLIENT", "PREMIUM", (255, 116, 205)
    return "MEMBER", "FREE PLAN", (156, 132, 255)


def _draw_pill(
    draw: ImageDraw.ImageDraw,
    position: tuple[int, int],
    text: str,
    *,
    font: Any,
    accent: tuple[int, int, int],
) -> int:
    left, top = position
    box = draw.textbbox((0, 0), text, font=font)
    width = box[2] - box[0] + 38
    draw.rounded_rectangle(
        (left, top, left + width, top + 48),
        radius=24,
        fill=tuple(max(0, channel - 150) for channel in accent),
        outline=accent,
        width=2,
    )
    draw.text((left + 19, top + 11), text, font=font, fill=accent)
    return width


def render_profile_card(payload: dict[str, Any]) -> bytes:
    image = Image.new("RGB", CARD_SIZE, (8, 11, 18))
    draw = ImageDraw.Draw(image)

    for radius in range(420, 60, -24):
        glow = max(0, 44 - (420 - radius) // 12)
        draw.ellipse(
            (900 - radius, 80 - radius, 900 + radius, 80 + radius),
            fill=(18 + glow // 3, 23 + glow // 2, 44 + glow),
        )
    for radius in range(340, 60, -24):
        glow = max(0, 34 - (340 - radius) // 12)
        draw.ellipse(
            (-80 - radius, 1080 - radius, -80 + radius, 1080 + radius),
            fill=(35 + glow, 17 + glow // 2, 49 + glow),
        )

    brand_font = _font(FONT_BOLD_PATHS, 35)
    micro_font = _font(FONT_BOLD_PATHS, 20)
    name_font = _font(FONT_BOLD_PATHS, 58)
    level_font = _font(FONT_BOLD_PATHS, 122)
    heading_font = _font(FONT_BOLD_PATHS, 38)
    metric_font = _font(FONT_BOLD_PATHS, 42)
    label_font = _font(FONT_REGULAR_PATHS, 24)
    small_font = _font(FONT_REGULAR_PATHS, 21)

    user = payload.get("user", {})
    progress = payload.get("global_progress", {})
    quick = payload.get("quick_stats", {})
    account = payload.get("account", {})
    role_label, plan_label, role_accent = _account_style(account)

    draw.text((70, 56), "CHATPULSE", font=brand_font, fill=(246, 247, 255))
    draw.text(
        (70, 103),
        "TELEGRAM PROFILE ANALYTICS",
        font=micro_font,
        fill=(133, 143, 169),
    )
    draw.rounded_rectangle(
        (930, 62, 1130, 118),
        radius=28,
        fill=(18, 23, 35),
        outline=(65, 75, 101),
        width=2,
    )
    draw.text((967, 80), "SHARE CARD", font=micro_font, fill=(154, 169, 202))

    draw.rounded_rectangle((70, 160, 1130, 1070), radius=58, fill=(18, 22, 35))
    draw.rounded_rectangle(
        (72, 162, 1128, 1068),
        radius=56,
        outline=(57, 64, 91),
        width=3,
    )

    initials = _fit(str(user.get("display_name") or "U"), 2).upper()
    draw.rounded_rectangle(
        (120, 218, 255, 353),
        radius=42,
        fill=(49, 41, 91),
        outline=(138, 112, 255),
        width=3,
    )
    initials_box = draw.textbbox((0, 0), initials, font=heading_font)
    initials_width = initials_box[2] - initials_box[0]
    draw.text(
        (187 - initials_width / 2, 260),
        initials,
        font=heading_font,
        fill=(255, 255, 255),
    )

    name = _fit(str(user.get("display_name") or "Учасник"), 25)
    username = user.get("username")
    draw.text((292, 218), name, font=name_font, fill=(249, 249, 255))
    draw.text(
        (296, 293),
        f"@{username}" if username else "Telegram profile",
        font=label_font,
        fill=(146, 155, 180),
    )
    _draw_pill(
        draw,
        (790, 225),
        role_label,
        font=micro_font,
        accent=role_accent,
    )
    _draw_pill(
        draw,
        (790, 284),
        plan_label,
        font=micro_font,
        accent=(104, 205, 255) if account.get("is_owner") else role_accent,
    )

    draw.line((120, 395, 1080, 395), fill=(47, 54, 77), width=2)

    draw.ellipse(
        (120, 445, 390, 715),
        fill=(28, 27, 52),
        outline=(142, 116, 255),
        width=5,
    )
    draw.text((211, 472), "LEVEL", font=micro_font, fill=(197, 184, 255))
    level = str(int(progress.get("level", 1)))
    level_box = draw.textbbox((0, 0), level, font=level_font)
    level_width = level_box[2] - level_box[0]
    draw.text(
        (255 - level_width / 2, 522),
        level,
        font=level_font,
        fill=(255, 255, 255),
    )

    tier = str(progress.get("tier", "Новачок"))
    xp_total = int(progress.get("xp_total", 0))
    current_progress = int(progress.get("progress", 0))
    level_needed = int(progress.get("needed", 0))
    ratio = 1.0 if level_needed <= 0 else min(1.0, max(0.0, current_progress / level_needed))

    draw.text((455, 455), tier, font=heading_font, fill=(207, 196, 255))
    draw.text(
        (455, 516),
        f"{xp_total:,} XP".replace(",", " "),
        font=metric_font,
        fill=(255, 255, 255),
    )
    if level_needed > 0:
        remaining = max(0, level_needed - current_progress)
        progress_copy = f"Ще {remaining:,} XP до наступного рівня".replace(",", " ")
    else:
        progress_copy = "Максимальний рівень досягнуто"
    draw.text((455, 579), progress_copy, font=label_font, fill=(145, 153, 177))

    draw.rounded_rectangle((455, 636, 1035, 654), radius=9, fill=(42, 47, 65))
    draw.rounded_rectangle(
        (455, 636, 455 + int(580 * ratio), 654),
        radius=9,
        fill=(124, 99, 255),
    )
    draw.text(
        (455, 673),
        "ГЛОБАЛЬНИЙ РЕЙТИНГ",
        font=micro_font,
        fill=(123, 132, 157),
    )
    rank = int(progress.get("rank", 0))
    percentile = int(progress.get("percentile", 0))
    draw.text(
        (805, 663),
        f"#{rank or '—'}",
        font=heading_font,
        fill=(255, 255, 255),
    )
    draw.text(
        (925, 681),
        f"TOP {max(1, 100 - percentile + 1)}%",
        font=micro_font,
        fill=(169, 147, 255),
    )

    metrics = (
        ("СЕРІЯ", int(quick.get("current_streak", 0)), "днів поспіль"),
        ("РЕКОРД", int(quick.get("longest_streak", 0)), "найкраща серія"),
        ("ЗАХИСТ", int(quick.get("protection_left", 0)), "днів цього місяця"),
        ("АКТИВНІСТЬ", int(quick.get("messages_7d", 0)), "повідомлень за 7 днів"),
    )
    positions = ((120, 770), (600, 770), (120, 905), (600, 905))
    for (label, value, suffix), (left, top) in zip(metrics, positions, strict=True):
        draw.rounded_rectangle(
            (left, top, left + 435, top + 110),
            radius=28,
            fill=(25, 30, 45),
            outline=(48, 56, 79),
            width=2,
        )
        draw.text(
            (left + 28, top + 20),
            label,
            font=micro_font,
            fill=(130, 140, 165),
        )
        draw.text(
            (left + 28, top + 52),
            str(value),
            font=metric_font,
            fill=(250, 250, 255),
        )
        draw.text(
            (left + 120, top + 65),
            suffix,
            font=small_font,
            fill=(139, 148, 171),
        )

    draw.text(
        (70, 1110),
        "Privacy-first analytics · texts are never stored",
        font=small_font,
        fill=(117, 126, 148),
    )
    draw.text((946, 1110), "ChatPulse", font=small_font, fill=(158, 135, 255))

    buffer = BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()
