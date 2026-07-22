from io import BytesIO
from typing import Any

from PIL import Image, ImageDraw

from app.services.report_cards import FONT_BOLD_PATHS, FONT_REGULAR_PATHS, _font

CARD_SIZE = (1200, 1200)


def _fit(value: str, limit: int) -> str:
    cleaned = " ".join(value.split())
    return cleaned if len(cleaned) <= limit else cleaned[: limit - 1].rstrip() + "…"


def render_profile_card(payload: dict[str, Any]) -> bytes:
    image = Image.new("RGB", CARD_SIZE, (10, 12, 20))
    draw = ImageDraw.Draw(image)

    # Ambient gradients using nested translucent circles.
    for radius in range(360, 40, -20):
        opacity = int(4 + (360 - radius) * 0.025)
        color = (44 + opacity, 32 + opacity, 82 + opacity)
        draw.ellipse((820 - radius, -110 - radius, 820 + radius, -110 + radius), fill=color)
    for radius in range(300, 50, -20):
        opacity = int(3 + (300 - radius) * 0.02)
        color = (12, 28 + opacity, 44 + opacity)
        draw.ellipse((-100 - radius, 1040 - radius, -100 + radius, 1040 + radius), fill=color)

    title_font = _font(FONT_BOLD_PATHS, 42)
    name_font = _font(FONT_BOLD_PATHS, 64)
    level_font = _font(FONT_BOLD_PATHS, 150)
    label_font = _font(FONT_REGULAR_PATHS, 28)
    metric_font = _font(FONT_BOLD_PATHS, 48)
    small_font = _font(FONT_REGULAR_PATHS, 24)

    user = payload.get("user", {})
    progress = payload.get("global_progress", {})
    quick = payload.get("quick_stats", {})

    draw.text((72, 62), "ChatPulse", font=title_font, fill=(147, 119, 255))
    draw.rounded_rectangle((72, 145, 1128, 1030), radius=56, fill=(24, 28, 43))
    draw.rounded_rectangle(
        (74, 147, 1126, 1028),
        radius=54,
        outline=(73, 66, 112),
        width=2,
    )

    draw.text((120, 205), "МІЙ CHATPULSE", font=label_font, fill=(157, 163, 185))
    name = _fit(str(user.get("display_name") or "Учасник"), 28)
    draw.text((120, 260), name, font=name_font, fill=(248, 248, 255))

    draw.ellipse((120, 380, 450, 710), fill=(35, 32, 66), outline=(141, 112, 255), width=5)
    draw.text((216, 407), "LEVEL", font=label_font, fill=(191, 178, 255))
    level = str(int(progress.get("level", 1)))
    level_box = draw.textbbox((0, 0), level, font=level_font)
    level_width = level_box[2] - level_box[0]
    draw.text((285 - level_width / 2, 452), level, font=level_font, fill=(255, 255, 255))

    draw.text((515, 405), str(progress.get("tier", "Новачок")), font=title_font, fill=(205, 193, 255))
    xp = f"{int(progress.get('xp_total', 0)):,}".replace(",", " ")
    draw.text((515, 480), f"{xp} XP", font=metric_font, fill=(255, 255, 255))
    rank = int(progress.get("rank", 0))
    draw.text((515, 555), f"Глобальне місце #{rank or '—'}", font=label_font, fill=(157, 163, 185))

    metrics = (
        ("🔥", "Серія", int(quick.get("current_streak", 0)), "днів"),
        ("🏆", "Рекорд", int(quick.get("longest_streak", 0)), "днів"),
        ("🛡", "Захист", int(quick.get("protection_left", 0)), "дні"),
        ("💬", "Активність", int(quick.get("messages_7d", 0)), "за 7 днів"),
    )
    card_width = 225
    gap = 20
    for index, (icon, label, value, suffix) in enumerate(metrics):
        left = 120 + index * (card_width + gap)
        draw.rounded_rectangle((left, 760, left + card_width, 930), radius=30, fill=(33, 37, 55))
        draw.text((left + 22, 784), icon, font=label_font, fill=(147, 119, 255))
        draw.text((left + 22, 828), str(value), font=metric_font, fill=(248, 248, 255))
        draw.text((left + 22, 885), f"{label} · {suffix}", font=small_font, fill=(151, 157, 178))

    draw.text(
        (72, 1095),
        "Privacy-first аналітика Telegram-груп",
        font=small_font,
        fill=(139, 145, 165),
    )
    draw.text((955, 1095), "@ChatPulse", font=small_font, fill=(147, 119, 255))

    buffer = BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()
