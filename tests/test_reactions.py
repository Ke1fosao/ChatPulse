from types import SimpleNamespace

from app.bot.routers.reactions import reaction_key


def test_reaction_key_supports_emoji_and_custom() -> None:
    assert reaction_key(SimpleNamespace(emoji="🔥")) == "🔥"
    assert reaction_key(SimpleNamespace(custom_emoji_id="123")) == "custom:123"
