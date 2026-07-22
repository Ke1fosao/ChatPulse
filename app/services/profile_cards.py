from io import BytesIO
from typing import Any

from PIL import Image, ImageDraw

from app.services.report_cards import FONT_BOLD_PATHS, FONT_REGULAR_PATHS, _font

CARD_SIZE = (1200, 1200)


def _fit(value: str, limit: int) -> str:
    cleaned = " ".join(value.split())
    return cleaned if len(cleaned) <= limit else cleaned[: limit - 1].rstrip() + "…"


def _role_label(account: dict[str, Any]) -> tuple[str, tuple[int, int, int]]:
    if account.get("is_owner"):
        return "OWNER · CREATOR", (247, 201, 101)
    if account.get("is_vip"):
        return "VIP CLIENT", (185, 142, 255)
    return "MEMBER · FREE", (117, 216, 255)


def _rounded_metric(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    label: str,
    value: str,
    caption: str,
    accent: tuple[int, int, int],
) -> None:
    left, top, right, bottom = box
    draw.rounded_rectangle(box, radius=30, fill=(25, 29, 43), outline=(48, 54, 76), width=2)
    draw.rounded_rectangle((left + 20, top + 20, left + 66, top + 66), radius=14, fill=accent)
    draw.text((left + 84, top + 21), label.upper(), font=_font(FONT_BOLD_PATHS, 22), fill=(154, 161, 184))
    draw.text((left + 24, top + 82), value, font=_font(FONT_BOLD_PATHS, 46), fill=(250, 250, 255))
    draw.text((left + 24, bottom - 45), caption, font=_font(FONT_REGULAR_PATHS, 22), fill=(139, 147, 171))


def render_profile_card(payload: dict[str, Any]) -> bytes:
    image = Image.new("RGB", CARD_SIZE, (8, 10, 17))
    draw = ImageDraw.Draw(image)

    for radius in range(460, 80, -24):
        glow = max(0, 30 - (460 - radius) // 16)
        draw.ellipse(
            (820 - radius, -150 - radius, 820 + radius, -150 + radius),
            fill=(35 + glow, 28 + glow // 2, 67 + glow),
        )
    for radius in range(360, 70, -22):
        glow = max(0, 18 - (360 - radius) // 20)
        draw.ellipse(
            (-120 - radius, 1110 - radius, -120 + radius, 1110 + radius),
            fill=(8, 25 + glow, 40 + glow),
        )

    user = payload.get("user", {})
    progress = payload.get("global_progress", {})
    quick = payload.get("quick_stats", {})
    account = payload.get("account", {})

    title_font = _font(FONT_BOLD_PATHS, 42)
    name_font = _font(FONT_BOLD_PATHS, 62)
    level_font = _font(FONT_BOLD_PATHS, 132)
    label_font = _font(FONT_BOLD_PATHS, 25)
    body_font = _font(FONT_REGULAR_PATHS, 26)
    metric_font = _font(FONT_BOLD_PATHS, 50)
    small_font = _font(FONT_REGULAR_PATHS, 22)

    draw.text((72, 58), "ChatPulse", font=title_font, fill=(164, 140, 255))
    draw.text((928, 72), "PROFILE CARD", font=label_font, fill=(111, 119, 143))

    draw.rounded_rectangle((62, 130, 1138, 1060), radius=56, fill=(17, 21, 33), outline=(54, 59, 82), width=2)
    draw.rounded_rectangle((92, 160, 1108, 360), radius=38, fill=(25, 29, 45))

    name = _fit(str(user.get("display_name") or "Учасник"), 26)
    username = user.get("username")
    draw.text((128, 198), "ТВІЙ CHATPULSE", font=label_font, fill=(157, 164, 188))
    draw.text((128, 246), name, font=name_font, fill=(251, 251, 255))
    draw.text(
        (128, 320),
        f"@{username}" if username else "Telegram profile",
        font=body_font,
        fill=(150, 158, 184),
    )

    role, role_color = _role_label(account)
    role_box = draw.textbbox((0, 0), role, font=label_font)
    role_width = role_box[2] - role_box[0]
    draw.rounded_rectangle((850 - role_width, 208, 1076, 276), radius=24, fill=(38, 40, 51), outline=role_color, width=2)
    draw.text((872 - role_width, 225), role, font=label_font, fill=role_color)

    draw.rounded_rectangle((92, 390, 1108, 690), radius=40, fill=(20, 24, 38), outline=(50, 56, 80), width=2)
    draw.ellipse((126, 430, 366, 670), fill=(31, 29, 58), outline=(137, 108, 255), width=5)
    draw.text((207, 455), "LEVEL", font=label_font, fill=(192, 179, 255))
    level = str(int(progress.get("level", 1)))
    level_box = draw.textbbox((0, 0), level, font=level_font)
    draw.text((246 - (level_box[2] - level_box[0]) / 2, 498), level, font=level_font, fill=(255, 255, 255))

    draw.text((414, 430), str(progress.get("tier", "Новачок")), font=title_font, fill=(211, 201, 255))
    xp = int(progress.get("xp_total", 0))
    draw.text((414, 500), f"{xp:,} XP".replace(",", " "), font=metric_font, fill=(255, 255, 255))

    current = int(progress.get("progress", 0))
    needed = max(1, int(progress.get("needed", 1)))
    ratio = max(0.0, min(1.0, current / needed))
    draw.rounded_rectangle((414, 578, 1036, 596), radius=9, fill=(44, 48, 65))
    draw.rounded_rectangle((414, 578, 414 + int(622 * ratio), 596), radius=9, fill=(132, 103, 255))
    draw.text((414, 612), f"{current:,} / {needed:,} XP до наступного рівня".replace(",", " "), font=small_font, fill=(145, 153, 177))

    metrics = (
        ("МІСЦЕ", f"#{int(progress.get('rank', 0)) or '—'}", "глобальний рейтинг", (64, 47, 102)),
        ("СЕРІЯ", str(int(quick.get("current_streak", 0))), "днів поспіль", (55, 42, 86)),
        ("ПОВІДОМЛЕННЯ", str(int(quick.get("messages_7d", 0))), "за останні 7 днів", (35, 65, 82)),
        ("ЗАХИСТ", str(int(quick.get("protection_left", 0))), "днів цього місяця", (31, 69, 69)),
    )
    positions = ((92, 724, 582, 860), (618, 724, 1108, 860), (92, 884, 582, 1020), (618, 884, 1108, 1020))
    for item, box in zip(metrics, positions, strict=True):
        label, value, caption, accent = item
        _rounded_metric(draw, box, label, value, caption, accent)

    draw.text((72, 1112), "Privacy-first Telegram analytics", font=small_font, fill=(129, 137, 160))
    draw.text((935, 1112), "CHATPULSE", font=label_font, fill=role_color)

    buffer = BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()
