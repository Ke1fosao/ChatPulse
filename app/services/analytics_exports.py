from __future__ import annotations

import csv
from io import BytesIO, StringIO
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont


def render_group_csv(dashboard: dict[str, Any]) -> bytes:
    output = StringIO(newline="")
    writer = csv.writer(output)
    group = dashboard["group"]
    summary = dashboard["overview"]["current"]
    writer.writerow(["ChatPulse VIP export"])
    writer.writerow(["Group", group["title"]])
    writer.writerow(["Period", dashboard["period"]])
    writer.writerow([])
    writer.writerow(["Metric", "Value"])
    for key in (
        "messages_count",
        "media_count",
        "replies_count",
        "reactions_received",
        "xp_earned",
        "active_members",
    ):
        writer.writerow([key, int(summary.get(key, 0))])
    writer.writerow([])
    writer.writerow(["Date", "XP", "Messages", "Reactions", "Replies"])
    for point in dashboard.get("activity_series", []):
        writer.writerow(
            [
                point.get("date", ""),
                int(point.get("xp", 0)),
                int(point.get("messages", 0)),
                int(point.get("reactions", 0)),
                int(point.get("replies", 0)),
            ]
        )
    return output.getvalue().encode("utf-8-sig")


def render_group_pdf(dashboard: dict[str, Any]) -> bytes:
    width, height = 1240, 1754
    image = Image.new("RGB", (width, height), "#0a0d16")
    draw = ImageDraw.Draw(image)
    title_font = _font(54, bold=True)
    heading_font = _font(31, bold=True)
    body_font = _font(25)
    small_font = _font(21)

    group = dashboard["group"]
    summary = dashboard["overview"]["current"]
    draw.text((72, 65), "ChatPulse VIP", font=title_font, fill="#ffffff")
    draw.text((72, 138), str(group["title"]), font=heading_font, fill="#9fe8ff")
    draw.text(
        (72, 186),
        f"Аналітика · період: {dashboard['period']}",
        font=body_font,
        fill="#aeb7cb",
    )

    metrics = [
        ("Повідомлення", summary.get("messages_count", 0)),
        ("XP", summary.get("xp_earned", 0)),
        ("Реакції", summary.get("reactions_received", 0)),
        ("Відповіді", summary.get("replies_count", 0)),
        ("Медіа", summary.get("media_count", 0)),
        ("Активні учасники", summary.get("active_members", 0)),
    ]
    y = 265
    for index, (label, value) in enumerate(metrics):
        column = index % 2
        row = index // 2
        x = 72 + column * 550
        card_y = y + row * 145
        draw.rounded_rectangle(
            (x, card_y, x + 505, card_y + 112),
            radius=24,
            fill="#141a29",
            outline="#273149",
            width=2,
        )
        draw.text((x + 24, card_y + 18), label, font=small_font, fill="#9aa6bf")
        draw.text((x + 24, card_y + 52), str(int(value or 0)), font=heading_font, fill="#ffffff")

    y = 735
    draw.text((72, y), "Активність за днями", font=heading_font, fill="#ffffff")
    y += 58
    draw.text(
        (72, y),
        "Дата             XP        Повідомлення     Реакції     Відповіді",
        font=small_font,
        fill="#8fdcf4",
    )
    y += 44
    for point in dashboard.get("activity_series", [])[-18:]:
        line = (
            f"{str(point.get('date', '')):<16}"
            f"{int(point.get('xp', 0)):>7}"
            f"{int(point.get('messages', 0)):>18}"
            f"{int(point.get('reactions', 0)):>12}"
            f"{int(point.get('replies', 0)):>12}"
        )
        draw.text((72, y), line, font=small_font, fill="#d8deeb")
        y += 42
        if y > 1600:
            break

    draw.text(
        (72, 1680),
        "Створено ChatPulse · тексти повідомлень не зберігаються",
        font=small_font,
        fill="#69748c",
    )
    output = BytesIO()
    image.save(output, format="PDF", resolution=150.0)
    return output.getvalue()


def _font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    names = (
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
        "Arial Bold.ttf" if bold else "Arial.ttf",
    )
    candidates = [
        Path("/usr/share/fonts/truetype/dejavu") / names[0],
        Path("/usr/share/fonts") / names[0],
        Path(names[1]),
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(str(path), size)
        except OSError:
            continue
    return ImageFont.load_default()
