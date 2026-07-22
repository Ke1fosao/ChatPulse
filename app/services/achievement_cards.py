from __future__ import annotations

from datetime import datetime
from io import BytesIO
from typing import Any

from PIL import Image, ImageDraw

from app.services.report_cards import FONT_BOLD_PATHS, FONT_REGULAR_PATHS, _font

CARD_SIZE = (1080, 1350)

RARITY_PALETTES: dict[str, dict[str, tuple[int, int, int]]] = {
    "common": {
        "accent": (91, 188, 255),
        "accent_2": (96, 119, 255),
        "surface": (18, 25, 39),
    },
    "uncommon": {
        "accent": (80, 223, 173),
        "accent_2": (58, 166, 135),
        "surface": (15, 31, 31),
    },
    "rare": {
        "accent": (155, 124, 255),
        "accent_2": (76, 201, 255),
        "surface": (27, 22, 47),
    },
    "epic": {
        "accent": (255, 103, 206),
        "accent_2": (141, 112, 255),
        "surface": (39, 20, 44),
    },
    "legendary": {
        "accent": (255, 213, 107),
        "accent_2": (255, 151, 67),
        "surface": (42, 33, 19),
    },
    "secret": {
        "accent": (240, 117, 255),
        "accent_2": (76, 233, 255),
        "surface": (29, 18, 37),
    },
}

RARITY_LABELS = {
    "common": "ЗВИЧАЙНЕ",
    "uncommon": "НЕЗВИЧАЙНЕ",
    "rare": "РІДКІСНЕ",
    "epic": "ЕПІЧНЕ",
    "legendary": "ЛЕГЕНДАРНЕ",
    "secret": "СЕКРЕТНЕ",
}


def _fit(value: str, limit: int) -> str:
    cleaned = " ".join(value.split())
    return cleaned if len(cleaned) <= limit else cleaned[: limit - 1].rstrip() + "…"


def _wrap_text(
    draw: ImageDraw.ImageDraw,
    value: str,
    *,
    font,
    max_width: int,
    max_lines: int,
) -> list[str]:
    words = " ".join(value.split()).split(" ")
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        box = draw.textbbox((0, 0), candidate, font=font)
        if box[2] - box[0] <= max_width:
            current = candidate
            continue
        if current:
            lines.append(current)
        current = word
        if len(lines) == max_lines:
            break
    if current and len(lines) < max_lines:
        lines.append(current)
    if len(lines) == max_lines and words:
        last = lines[-1]
        while last and draw.textbbox((0, 0), f"{last}…", font=font)[2] > max_width:
            last = last[:-1].rstrip()
        lines[-1] = f"{last}…" if last else "…"
    return lines


def _format_date(value: str | None) -> str:
    if not value:
        return "Щойно отримано"
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return "Щойно отримано"
    return parsed.strftime("%d.%m.%Y · %H:%M")


def render_achievement_card(
    event_payload: dict[str, Any],
    *,
    display_name: str,
    username: str | None,
) -> bytes:
    achievement = event_payload.get("achievement", {})
    rarity = str(achievement.get("rarity", "common"))
    palette = RARITY_PALETTES.get(rarity, RARITY_PALETTES["common"])
    accent = palette["accent"]
    accent_2 = palette["accent_2"]
    surface = palette["surface"]

    image = Image.new("RGB", CARD_SIZE, (7, 9, 16))
    draw = ImageDraw.Draw(image)

    for radius in range(620, 110, -26):
        intensity = max(0, 38 - (620 - radius) // 15)
        color = tuple(min(255, component // 7 + intensity) for component in accent)
        draw.ellipse(
            (820 - radius, 100 - radius, 820 + radius, 100 + radius),
            fill=color,
        )
    for radius in range(420, 90, -24):
        intensity = max(0, 20 - (420 - radius) // 18)
        color = tuple(min(255, component // 10 + intensity) for component in accent_2)
        draw.ellipse(
            (-80 - radius, 1230 - radius, -80 + radius, 1230 + radius),
            fill=color,
        )

    brand_font = _font(FONT_BOLD_PATHS, 34)
    label_font = _font(FONT_BOLD_PATHS, 22)
    rarity_font = _font(FONT_BOLD_PATHS, 24)
    title_font = _font(FONT_BOLD_PATHS, 68)
    description_font = _font(FONT_REGULAR_PATHS, 31)
    name_font = _font(FONT_BOLD_PATHS, 34)
    body_font = _font(FONT_REGULAR_PATHS, 25)
    chain_font = _font(FONT_BOLD_PATHS, 29)

    draw.text((64, 54), "ChatPulse", font=brand_font, fill=accent)
    draw.text((812, 65), "ACHIEVEMENT", font=label_font, fill=(136, 144, 168))

    draw.rounded_rectangle(
        (54, 126, 1026, 1248),
        radius=56,
        fill=(14, 17, 28),
        outline=tuple(min(255, component + 10) for component in surface),
        width=2,
    )
    draw.rounded_rectangle(
        (84, 156, 996, 1218),
        radius=42,
        fill=surface,
        outline=accent,
        width=2,
    )

    rarity_label = RARITY_LABELS.get(rarity, RARITY_LABELS["common"])
    rarity_box = draw.textbbox((0, 0), rarity_label, font=rarity_font)
    rarity_width = rarity_box[2] - rarity_box[0]
    draw.rounded_rectangle(
        (540 - rarity_width // 2 - 28, 196, 540 + rarity_width // 2 + 28, 252),
        radius=24,
        fill=(20, 23, 35),
        outline=accent,
        width=2,
    )
    draw.text(
        (540 - rarity_width // 2, 211),
        rarity_label,
        font=rarity_font,
        fill=accent,
    )

    draw.ellipse(
        (350, 300, 730, 680),
        fill=(18, 21, 34),
        outline=accent,
        width=5,
    )
    draw.ellipse(
        (390, 340, 690, 640),
        fill=surface,
        outline=accent_2,
        width=3,
    )
    icon_label = "?" if rarity == "secret" else str(achievement.get("title", "A"))[:1].upper()
    icon_font = _font(FONT_BOLD_PATHS, 154)
    icon_box = draw.textbbox((0, 0), icon_label, font=icon_font)
    draw.text(
        (
            540 - (icon_box[2] - icon_box[0]) / 2,
            405 - (icon_box[3] - icon_box[1]) / 4,
        ),
        icon_label,
        font=icon_font,
        fill=accent,
    )

    title = _fit(str(achievement.get("title") or "Нове досягнення"), 56)
    title_lines = _wrap_text(
        draw,
        title,
        font=title_font,
        max_width=820,
        max_lines=2,
    )
    title_top = 720
    for index, line in enumerate(title_lines):
        box = draw.textbbox((0, 0), line, font=title_font)
        draw.text(
            (540 - (box[2] - box[0]) / 2, title_top + index * 78),
            line,
            font=title_font,
            fill=(250, 250, 255),
        )

    description = str(achievement.get("description") or "Досягнення розблоковано")
    description_lines = _wrap_text(
        draw,
        description,
        font=description_font,
        max_width=760,
        max_lines=3,
    )
    description_top = title_top + len(title_lines) * 78 + 24
    for index, line in enumerate(description_lines):
        box = draw.textbbox((0, 0), line, font=description_font)
        draw.text(
            (540 - (box[2] - box[0]) / 2, description_top + index * 43),
            line,
            font=description_font,
            fill=(183, 191, 213),
        )

    meta_top = min(1050, description_top + len(description_lines) * 43 + 42)
    group_title = _fit(
        str(achievement.get("group_title") or "Глобальний профіль ChatPulse"),
        40,
    )
    chain = achievement.get("chain")
    chain_label = None
    if isinstance(chain, dict):
        chain_label = f"Етап {int(chain.get('stage', 0))} з {int(chain.get('total', 0))}"

    draw.rounded_rectangle(
        (112, meta_top, 968, meta_top + 116),
        radius=28,
        fill=(13, 16, 27),
        outline=(56, 62, 84),
        width=2,
    )
    draw.text((142, meta_top + 20), _fit(display_name, 28), font=name_font, fill=(250, 250, 255))
    profile_line = f"@{username}" if username else "Telegram profile"
    draw.text((142, meta_top + 66), profile_line, font=body_font, fill=(145, 154, 177))

    group_box = draw.textbbox((0, 0), group_title, font=body_font)
    draw.text(
        (938 - (group_box[2] - group_box[0]), meta_top + 22),
        group_title,
        font=body_font,
        fill=accent,
    )
    date_label = _format_date(str(achievement.get("earned_at") or ""))
    date_box = draw.textbbox((0, 0), date_label, font=body_font)
    draw.text(
        (938 - (date_box[2] - date_box[0]), meta_top + 68),
        date_label,
        font=body_font,
        fill=(139, 147, 171),
    )

    if chain_label:
        chain_box = draw.textbbox((0, 0), chain_label, font=chain_font)
        chain_width = chain_box[2] - chain_box[0]
        draw.rounded_rectangle(
            (540 - chain_width // 2 - 22, 1162, 540 + chain_width // 2 + 22, 1211),
            radius=20,
            fill=(17, 20, 31),
            outline=accent_2,
            width=2,
        )
        draw.text(
            (540 - chain_width // 2, 1172),
            chain_label,
            font=chain_font,
            fill=accent_2,
        )

    draw.text((64, 1290), "chatpulse · privacy-first", font=body_font, fill=(126, 134, 157))
    draw.text((848, 1290), "SHARE CARD", font=label_font, fill=accent)

    buffer = BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()
