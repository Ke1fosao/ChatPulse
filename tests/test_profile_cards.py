from io import BytesIO

from PIL import Image

from app.services.profile_cards import render_profile_card


def test_profile_card_is_valid_1200_square_png() -> None:
    image_bytes = render_profile_card(
        {
            "user": {"display_name": "Дмитро Ковтунович"},
            "global_progress": {
                "level": 7,
                "tier": "Срібло",
                "xp_total": 4250,
                "rank": 3,
            },
            "quick_stats": {
                "current_streak": 18,
                "longest_streak": 31,
                "protection_left": 2,
                "messages_7d": 248,
            },
        }
    )

    image = Image.open(BytesIO(image_bytes))
    assert image.format == "PNG"
    assert image.size == (1200, 1200)
