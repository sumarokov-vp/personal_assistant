import logging
from unittest.mock import Mock

import pytest

from workers.bot import __main__ as bot_main


@pytest.mark.parametrize("rabbitmq_url", [None, ""])
def test_consumer_does_not_start_without_rabbitmq_url(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    rabbitmq_url: str | None,
) -> None:
    thread_factory = Mock()
    monkeypatch.setattr(bot_main, "Thread", thread_factory)

    with caplog.at_level(logging.INFO):
        started = bot_main.start_agent_notifications(
            rabbitmq_url=rabbitmq_url,
            database_url="postgres://unused",
            app=Mock(),
            owner_telegram_id=42,
            dropbox_boundary=None,
        )

    assert started is None
    thread_factory.assert_not_called()
    assert "RABBITMQ_URL is not set" in caplog.text
