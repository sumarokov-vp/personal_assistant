import logging
from typing import Any
from unittest.mock import MagicMock
from urllib.parse import unquote

import pytest
from telebot import TeleBot
from telebot.types import InlineKeyboardMarkup

from src.flows.recordings.services import ConsoleRecordingOutcome, RecordingLinks
from workers.bot.recording_check import build_check_outcome, build_parser

OWNER_CHAT_ID = 4242
SENT_MESSAGE_ID = 777
RECORDING_NAME = "Сверка выката.m4a"
TRANSCRIPT_PATH = "Записи разговоров/Сверка выката.json"


def owner_bot() -> MagicMock:
    bot = MagicMock(spec=TeleBot)
    bot.send_message.return_value = MagicMock(message_id=SENT_MESSAGE_ID)
    return bot


def console(lines: list[str]) -> ConsoleRecordingOutcome:
    return ConsoleRecordingOutcome(links=RecordingLinks(), write=lines.append)


def test_flag_is_off_by_default() -> None:
    assert build_parser().parse_args(["x.m4a"]).notify_owner is False
    assert build_parser().parse_args(["x.m4a", "--notify-owner"]).notify_owner is True


def test_without_flag_only_console_is_written() -> None:
    lines: list[str] = []
    outcome = build_check_outcome(console(lines), owner_bot=None)

    outcome.ready(OWNER_CHAT_ID, RECORDING_NAME, TRANSCRIPT_PATH)

    assert lines[0] == f"ok: {RECORDING_NAME} -> {TRANSCRIPT_PATH}"


def test_notify_owner_sends_link_and_protocol_buttons(
    caplog: pytest.LogCaptureFixture,
) -> None:
    lines: list[str] = []
    bot = owner_bot()
    outcome = build_check_outcome(console(lines), owner_bot=bot)

    with caplog.at_level(logging.INFO):
        outcome.ready(OWNER_CHAT_ID, RECORDING_NAME, TRANSCRIPT_PATH)

    assert lines[0] == f"ok: {RECORDING_NAME} -> {TRANSCRIPT_PATH}"
    bot.send_message.assert_called_once()
    args: Any = bot.send_message.call_args
    assert args.args[0] == OWNER_CHAT_ID
    text: str = args.args[1]
    assert "dropbox.com/home/" in text
    assert RECORDING_NAME in text
    markup: InlineKeyboardMarkup = args.kwargs["reply_markup"]
    buttons = [button for row in markup.keyboard for button in row]
    assert [button.text for button in buttons] == [
        "Протокол встречи",
        "Протокол звонка",
    ]
    assert all(
        TRANSCRIPT_PATH in unquote(button.url or "").replace("+", " ")
        for button in buttons
    )
    assert f"message_id {SENT_MESSAGE_ID}" in caplog.text


def test_notify_owner_reports_failure_to_owner(
    caplog: pytest.LogCaptureFixture,
) -> None:
    lines: list[str] = []
    bot = owner_bot()
    outcome = build_check_outcome(console(lines), owner_bot=bot)

    with caplog.at_level(logging.INFO):
        outcome.failed(OWNER_CHAT_ID, RECORDING_NAME, "сервис распознавания недоступен")

    assert lines == [f"failed: {RECORDING_NAME}: сервис распознавания недоступен"]
    assert bot.send_message.call_args.args[0] == OWNER_CHAT_ID
    assert "не распознана" in bot.send_message.call_args.args[1]
    assert f"message_id {SENT_MESSAGE_ID}" in caplog.text
