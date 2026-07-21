from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

CARD_SIZE = (1200, 1200)
FONT_REGULAR_PATHS = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans.ttf",
)
FONT_BOLD_PATHS = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
)

THEMES: dict[str, dict[str, tuple[int, int, int]]] = {
    "dark_pulse": {
        "background": (18, 18, 28),
        "panel": (34, 31, 52),
        "primary": (244, 241, 255),
        "secondary": (187, 179, 214),
        "accent": (145, 96, 255),
    },
    "telegram_wave": {
        "background": (26, 111, 211),
        "panel": (47, 65, 166),
        "primary": (255, 255, 255),
        "secondary": (221, 235, 255),
        "accent": (151, 108, 255),
    },
    "clean_light": {
        "background": (246, 247, 251),
        "panel": (255, 255, 255),
        "primary": (31, 35, 48),
        "secondary": (96, 102, 122),
        "accent": (92, 78, 214),
    },
}


def _font(
    paths: tuple[str, ...],
    size: int,
) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in paths:
        if Path(path).exists():
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def _rounded_panel(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    fill: tuple[int, int, int],
    radius: int = 36,
) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill)


def _fit_text(value: str, limit: int) -> str:
    cleaned = " ".join(value.split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: max(0, limit - 1)].rstrip() + "…"


def render_weekly_report_card(payload: dict[str, Any], theme_name: str) -> bytes:
    theme = THEMES.get(theme_name, THEMES["dark_pulse"])
    image = Image.new("RGB", CARD_SIZE, theme["background"])
    draw = ImageDraw.Draw(image)

    title_font = _font(FONT_BOLD_PATHS, 62)
    subtitle_font = _font(FONT_REGULAR_PATHS, 28)
    metric_font = _font(FONT_BOLD_PATHS, 50)
    metric_label_font = _font(FONT_REGULAR_PATHS, 24)
    section_font = _font(FONT_BOLD_PATHS, 34)
    body_font = _font(FONT_REGULAR_PATHS, 27)
    small_font = _font(FONT_REGULAR_PATHS, 22)

    group_title = _fit_text(str(payload.get("group_title", "ChatPulse")), 32)
    draw.text((70, 58), "ChatPulse", font=subtitle_font, fill=theme["accent"])
    draw.text((70, 100), "Підсумки тижня", font=title_font, fill=theme["primary"])
    draw.text((72, 180), group_title, font=subtitle_font, fill=theme["secondary"])

    summary = payload.get("summary", {})
    metrics = (
        ("messages_count", "Повідомлень", "💬"),
        ("reactions_received", "Реакцій", "❤️"),
        ("active_members", "Учасників", "👥"),
        ("media_count", "Медіа", "🖼"),
    )
    card_width = 245
    gap = 22
    start_x = 70
    top = 245
    for index, (key, label, icon) in enumerate(metrics):
        left = start_x + index * (card_width + gap)
        _rounded_panel(draw, (left, top, left + card_width, top + 185), theme["panel"], 30)
        draw.text((left + 24, top + 18), icon, font=subtitle_font, fill=theme["accent"])
        draw.text(
            (left + 24, top + 60),
            f"{int(summary.get(key, 0)):,}".replace(",", " "),
            font=metric_font,
            fill=theme["primary"],
        )
        draw.text(
            (left + 24, top + 130),
            label,
            font=metric_label_font,
            fill=theme["secondary"],
        )

    _rounded_panel(draw, (70, 465, 1130, 720), theme["panel"], 36)
    draw.text((105, 495), "Номінації", font=section_font, fill=theme["primary"])
    nominations = list(payload.get("nominations", []))[:4]
    if nominations:
        y = 548
        for item in nominations:
            draw.text(
                (105, y),
                _fit_text(str(item), 62),
                font=body_font,
                fill=theme["secondary"],
            )
            y += 43
    else:
        draw.text(
            (105, 560),
            "Поки недостатньо активності",
            font=body_font,
            fill=theme["secondary"],
        )

    _rounded_panel(draw, (70, 750, 1130, 1045), theme["panel"], 36)
    draw.text((105, 780), "Головне за тиждень", font=section_font, fill=theme["primary"])
    y = 835
    comparison = payload.get("comparison_line")
    if comparison:
        draw.text(
            (105, y),
            _fit_text(str(comparison), 70),
            font=body_font,
            fill=theme["secondary"],
        )
        y += 48
    top_message = payload.get("top_message")
    if top_message:
        line = (
            f"🔥 Повідомлення тижня: {top_message['display_name']} — "
            f"{int(top_message['reactions_count'])} реакцій"
        )
        draw.text(
            (105, y),
            _fit_text(line, 70),
            font=body_font,
            fill=theme["secondary"],
        )
        y += 48
    achievements = list(payload.get("achievements", []))[:2]
    for item in achievements:
        line = f"🏅 {item['display_name']}: {item['title']}"
        draw.text(
            (105, y),
            _fit_text(line, 70),
            font=body_font,
            fill=theme["secondary"],
        )
        y += 48
    if not comparison and not top_message and not achievements:
        draw.text(
            (105, y),
            "Нові рекорди ще попереду",
            font=body_font,
            fill=theme["secondary"],
        )

    draw.text(
        (70, 1110),
        "Статистика без збереження текстів повідомлень",
        font=small_font,
        fill=theme["secondary"],
    )
    draw.text((1020, 1110), "@ChatPulse", font=small_font, fill=theme["accent"])

    buffer = BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()
