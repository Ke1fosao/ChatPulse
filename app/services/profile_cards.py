from io import BytesIO
from typing import Any

from PIL import Image, ImageDraw

from app.services.report_cards import FONT_BOLD_PATHS, FONT_REGULAR_PATHS, _font

CARD_SIZE = (1200, 1200)

_RARITY_ACCENTS: dict[str, tuple[int, int, int]] = {
    "common": (104, 185, 255),
    "uncommon": (80, 223, 173),
    "rare": (155, 124, 255),
    "epic": (255, 103, 206),
    "legendary": (255, 213, 107),
    "secret": (239, 117, 255),
}


def _fit(value: str, limit: int) -> str:
    cleaned = " ".join(value.split())
    return cleaned if len(cleaned) <= limit else cleaned[: limit - 1].rstrip() + "…"


def _role_label(account: dict[str, Any]) -> tuple[str, tuple[int, int, int]]:
    if account.get("is_owner"):
        return "OWNER", (247, 201, 101)
    if account.get("is_vip"):
        return "VIP", (185, 142, 255)
    return "FREE", (117, 216, 255)


def _metric(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    label: str,
    value: str,
    caption: str,
    accent: tuple[int, int, int],
) -> None:
    left, top, right, bottom = box
    draw.rounded_rectangle(
        box,
        radius=30,
        fill=(22, 26, 40),
        outline=(48, 55, 78),
        width=2,
    )
    draw.rounded_rectangle(
        (left + 24, top + 24, left + 44, top + 44),
        radius=8,
        fill=accent,
    )
    draw.text(
        (left + 58, top + 20),
        label.upper(),
        font=_font(FONT_BOLD_PATHS, 20),
        fill=(153, 162, 188),
    )
    draw.text(
        (left + 24, top + 62),
        value,
        font=_font(FONT_BOLD_PATHS, 44),
        fill=(250, 251, 255),
    )
    draw.text(
        (left + 24, bottom - 42),
        caption,
        font=_font(FONT_REGULAR_PATHS, 19),
        fill=(132, 142, 168),
    )


def _achievement_mark(
    draw: ImageDraw.ImageDraw,
    *,
    center: tuple[int, int],
    icon: str,
    accent: tuple[int, int, int],
) -> None:
    x, y = center
    pale = tuple(min(255, value + 50) for value in accent)
    if icon in {"message-circle", "reply"}:
        draw.rounded_rectangle((x - 16, y - 13, x + 16, y + 10), radius=7, outline=pale, width=4)
        draw.polygon(((x - 6, y + 9), (x - 13, y + 18), (x + 1, y + 10)), fill=pale)
    elif icon in {"heart"}:
        draw.ellipse((x - 15, y - 12, x + 1, y + 4), fill=pale)
        draw.ellipse((x - 1, y - 12, x + 15, y + 4), fill=pale)
        draw.polygon(((x - 15, y - 3), (x + 15, y - 3), (x, y + 18)), fill=pale)
    elif icon in {"image", "gallery-horizontal"}:
        draw.rounded_rectangle((x - 17, y - 15, x + 17, y + 15), radius=5, outline=pale, width=4)
        draw.ellipse((x + 5, y - 9, x + 11, y - 3), fill=pale)
        draw.polygon(
            ((x - 13, y + 10), (x - 4, y), (x + 2, y + 6), (x + 8, y), (x + 14, y + 10)), fill=pale
        )
    elif icon in {"flame", "zap", "cloud-lightning"}:
        draw.polygon(
            (
                (x + 2, y - 19),
                (x - 13, y + 2),
                (x - 2, y + 2),
                (x - 7, y + 19),
                (x + 14, y - 5),
                (x + 3, y - 5),
            ),
            fill=pale,
        )
    elif icon in {"crown", "trophy", "medal"}:
        draw.polygon(
            (
                (x - 17, y - 12),
                (x - 8, y + 4),
                (x, y - 9),
                (x + 8, y + 4),
                (x + 17, y - 12),
                (x + 13, y + 12),
                (x - 13, y + 12),
            ),
            fill=pale,
        )
        draw.rectangle((x - 10, y + 14, x + 10, y + 18), fill=pale)
    else:
        draw.line((x, y - 18, x, y + 18), fill=pale, width=4)
        draw.line((x - 18, y, x + 18, y), fill=pale, width=4)
        draw.line((x - 12, y - 12, x + 12, y + 12), fill=pale, width=3)
        draw.line((x - 12, y + 12, x + 12, y - 12), fill=pale, width=3)


def _featured_row(draw: ImageDraw.ImageDraw, items: list[dict[str, Any]]) -> None:
    draw.rounded_rectangle(
        (84, 824, 1116, 918),
        radius=28,
        fill=(19, 23, 37),
        outline=(53, 59, 83),
        width=2,
    )
    draw.text((108, 840), "ВІТРИНА НАГОРОД", font=_font(FONT_BOLD_PATHS, 17), fill=(153, 162, 188))
    safe_items = items[:5]
    if not safe_items:
        draw.text(
            (108, 875),
            "Закріплені нагороди зʼявляться тут",
            font=_font(FONT_REGULAR_PATHS, 18),
            fill=(122, 132, 157),
        )
        return

    available_width = 970
    item_width = available_width // len(safe_items)
    start_x = 112
    for index, item in enumerate(safe_items):
        accent = _RARITY_ACCENTS.get(str(item.get("rarity", "common")), _RARITY_ACCENTS["common"])
        left = start_x + index * item_width
        icon_center = (left + 24, 884)
        draw.ellipse(
            (icon_center[0] - 22, icon_center[1] - 22, icon_center[0] + 22, icon_center[1] + 22),
            fill=tuple(max(0, value // 5) for value in accent),
            outline=accent,
            width=2,
        )
        _achievement_mark(
            draw,
            center=icon_center,
            icon=str(item.get("icon", "sparkles")),
            accent=accent,
        )
        draw.text(
            (left + 54, 868),
            _fit(str(item.get("title") or "Нагорода"), 14),
            font=_font(FONT_BOLD_PATHS, 16),
            fill=(245, 246, 252),
        )
        draw.text(
            (left + 54, 892),
            _fit(str(item.get("group_title") or "Глобальна"), 15),
            font=_font(FONT_REGULAR_PATHS, 14),
            fill=accent,
        )


def render_profile_card(payload: dict[str, Any]) -> bytes:
    image = Image.new("RGB", CARD_SIZE, (7, 9, 16))
    draw = ImageDraw.Draw(image)

    for radius in range(500, 80, -28):
        glow = max(0, 28 - (500 - radius) // 18)
        draw.ellipse(
            (1040 - radius, 70 - radius, 1040 + radius, 70 + radius),
            fill=(26 + glow, 21 + glow // 2, 55 + glow),
        )
    for radius in range(330, 70, -24):
        glow = max(0, 16 - (330 - radius) // 20)
        draw.ellipse(
            (-90 - radius, 1120 - radius, -90 + radius, 1120 + radius),
            fill=(7, 22 + glow, 34 + glow),
        )

    user = payload.get("user", {})
    progress = payload.get("global_progress", {})
    quick = payload.get("quick_stats", {})
    account = payload.get("account", {})
    featured = list(payload.get("featured_achievements", []))

    name = _fit(str(user.get("display_name") or "Учасник"), 24)
    username = user.get("username")
    role, role_color = _role_label(account)
    level = int(progress.get("level", 1))
    xp = int(progress.get("xp_total", 0))
    current = int(progress.get("progress", 0))
    needed = max(1, int(progress.get("needed", 1)))
    ratio = max(0.0, min(1.0, current / needed))
    streak = int(quick.get("current_streak", 0))

    title_font = _font(FONT_BOLD_PATHS, 36)
    name_font = _font(FONT_BOLD_PATHS, 60)
    tier_font = _font(FONT_BOLD_PATHS, 35)
    level_font = _font(FONT_BOLD_PATHS, 104)
    metric_font = _font(FONT_BOLD_PATHS, 46)
    label_font = _font(FONT_BOLD_PATHS, 20)
    body_font = _font(FONT_REGULAR_PATHS, 23)
    small_font = _font(FONT_REGULAR_PATHS, 18)

    draw.text((70, 52), "ChatPulse", font=title_font, fill=(174, 151, 255))
    draw.text((940, 65), "PROFILE", font=label_font, fill=(111, 120, 145))

    draw.rounded_rectangle(
        (54, 124, 1146, 1090),
        radius=50,
        fill=(14, 18, 29),
        outline=(49, 56, 80),
        width=2,
    )

    draw.rounded_rectangle((84, 154, 1116, 320), radius=34, fill=(23, 27, 43))
    draw.text((116, 184), "ТВІЙ CHATPULSE", font=label_font, fill=(150, 159, 185))
    draw.text((116, 222), name, font=name_font, fill=(252, 252, 255))
    draw.text(
        (116, 286),
        f"@{username}" if username else "Telegram profile",
        font=body_font,
        fill=(145, 154, 181),
    )
    role_box = draw.textbbox((0, 0), role, font=label_font)
    role_width = role_box[2] - role_box[0]
    role_left = 1074 - role_width - 34
    draw.rounded_rectangle(
        (role_left, 202, 1074, 258),
        radius=20,
        fill=(31, 34, 46),
        outline=role_color,
        width=2,
    )
    draw.text((role_left + 20, 218), role, font=label_font, fill=role_color)

    draw.rounded_rectangle(
        (84, 350, 1116, 610),
        radius=38,
        fill=(18, 22, 36),
        outline=(66, 57, 106),
        width=2,
    )
    draw.ellipse(
        (120, 386, 324, 590),
        fill=(30, 27, 56),
        outline=(142, 109, 255),
        width=4,
    )
    draw.text((174, 402), "LEVEL", font=label_font, fill=(196, 183, 255))
    level_text = str(level)
    level_box = draw.textbbox((0, 0), level_text, font=level_font)
    draw.text(
        (222 - (level_box[2] - level_box[0]) / 2, 446),
        level_text,
        font=level_font,
        fill=(255, 255, 255),
    )
    draw.text(
        (366, 392),
        str(progress.get("tier", "Новачок")),
        font=tier_font,
        fill=(215, 205, 255),
    )
    draw.text(
        (366, 450),
        f"{xp:,} XP".replace(",", " "),
        font=metric_font,
        fill=(255, 255, 255),
    )
    draw.rounded_rectangle((366, 526, 1046, 542), radius=8, fill=(43, 48, 66))
    if ratio > 0:
        draw.rounded_rectangle(
            (366, 526, 366 + max(16, int(680 * ratio)), 542),
            radius=8,
            fill=(135, 105, 255),
        )
    progress_label = f"{current:,} / {needed:,} XP до наступного рівня".replace(",", " ")
    draw.text((366, 560), progress_label, font=small_font, fill=(137, 147, 174))

    metrics = (
        (
            "МІСЦЕ",
            f"#{int(progress.get('rank', 0)) or '—'}",
            "у глобальному рейтингу",
            (91, 63, 145),
        ),
        ("ПОВІДОМЛЕННЯ", str(int(quick.get("messages_7d", 0))), "за останні 7 днів", (31, 83, 102)),
        ("ЗАХИСТ", str(int(quick.get("protection_left", 0))), "днів залишилось", (27, 89, 77)),
    )
    metric_boxes = (
        (84, 640, 414, 806),
        (435, 640, 765, 806),
        (786, 640, 1116, 806),
    )
    for item, box in zip(metrics, metric_boxes, strict=True):
        _metric(draw, box, *item)

    _featured_row(draw, featured)

    streak_outline = (255, 139, 75) if streak > 0 else (117, 93, 105)
    draw.rounded_rectangle(
        (84, 936, 1116, 1058),
        radius=31,
        fill=(37, 23, 31),
        outline=streak_outline,
        width=3,
    )
    draw.ellipse((112, 952, 204, 1044), fill=(67, 35, 32), outline=streak_outline, width=3)
    draw.text((137, 967), "🔥", font=_font(FONT_REGULAR_PATHS, 44), fill=(255, 170, 87))
    draw.text((238, 954), "ТВІЙ ВОГНИК", font=label_font, fill=(245, 184, 149))
    draw.text((238, 986), f"{streak} днів", font=_font(FONT_BOLD_PATHS, 35), fill=(255, 255, 255))
    streak_caption = (
        "Тримай ритм — наступний активний день продовжить серію."
        if streak > 0
        else "Почни серію сьогодні — напиши повідомлення в активній групі."
    )
    draw.text((470, 990), streak_caption, font=_font(FONT_REGULAR_PATHS, 18), fill=(196, 159, 151))

    draw.text((72, 1125), "Privacy-first Telegram analytics", font=small_font, fill=(122, 132, 157))
    draw.text((950, 1125), "CHATPULSE", font=label_font, fill=role_color)

    buffer = BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()
