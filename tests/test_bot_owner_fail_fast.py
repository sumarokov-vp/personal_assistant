from unittest.mock import Mock

import pytest

from workers.bot import __main__ as bot_main


@pytest.fixture
def bot_application(monkeypatch: pytest.MonkeyPatch) -> Mock:
    application = Mock()
    monkeypatch.setattr(bot_main, "load_dotenv", Mock())
    monkeypatch.setattr(bot_main, "BotApplication", application)
    monkeypatch.setenv("BOT_TOKEN", "1:test")
    monkeypatch.setenv("BOT_DB_URL", "postgres://unused")
    monkeypatch.setenv("REDIS_URL", "redis://unused")
    monkeypatch.setenv("AI_DB_URL", "postgres://unused")
    monkeypatch.setenv("AI_MODEL", "unused")
    return application


def test_main_fails_before_polling_without_owner_id(
    monkeypatch: pytest.MonkeyPatch, bot_application: Mock
) -> None:
    monkeypatch.delenv("OWNER_TELEGRAM_ID", raising=False)

    with pytest.raises(ValueError, match="OWNER_TELEGRAM_ID"):
        bot_main.main()

    bot_application.assert_not_called()


@pytest.mark.parametrize("value", ["owner", "12a", "-5", " "])
def test_main_fails_before_polling_on_non_numeric_owner_id(
    monkeypatch: pytest.MonkeyPatch, bot_application: Mock, value: str
) -> None:
    monkeypatch.setenv("OWNER_TELEGRAM_ID", value)

    with pytest.raises(ValueError, match="OWNER_TELEGRAM_ID"):
        bot_main.main()

    bot_application.assert_not_called()
