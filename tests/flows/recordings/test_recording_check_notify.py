import logging
from typing import Any
from unittest.mock import MagicMock

import pytest
from telebot import TeleBot
from telebot.types import InlineKeyboardMarkup

from src.flows.recordings.services import (
    ConsoleRecordingOutcome,
    ProtocolCallback,
    RecordedTranscript,
    RecordingLinks,
)
from workers.bot.recording_check import build_check_outcome, build_parser

OWNER_CHAT_ID = 4242
SENT_MESSAGE_ID = 777
RECORDING_NAME = "Сверка выката.m4a"
TRANSCRIPT_PATH = "Записи разговоров/Сверка выката.json"
TRANSCRIPT = RecordedTranscript(
    transcript_id="0a1b2c3d",
    recording_name=RECORDING_NAME,
    transcript_path=TRANSCRIPT_PATH,
    recorded_on="09.11.2026",
    result={"segments": []},
)


def owner_bot() -> MagicMock:
    bot = MagicMock(spec=TeleBot)
    bot.send_message.return_value = MagicMock(message_id=SENT_MESSAGE_ID)
    return bot


def console(lines: list[str]) -> ConsoleRecordingOutcome:
    return ConsoleRecordingOutcome(
        links=RecordingLinks(), protocol_callback=ProtocolCallback(), write=lines.append
    )


def test_flag_is_off_by_default() -> None:
    assert build_parser().parse_args(["x.m4a"]).notify_owner is False
    assert build_parser().parse_args(["x.m4a", "--notify-owner"]).notify_owner is True
    assert build_parser().parse_args(["x.m4a"]).protocol is None
    assert build_parser().parse_args(["x.m4a", "--protocol", "call"]).protocol == "call"


def test_without_flag_only_console_is_written() -> None:
    lines: list[str] = []
    outcome = build_check_outcome(console(lines), owner_bot=None)

    outcome.ready(OWNER_CHAT_ID, TRANSCRIPT)

    assert lines == [
        f"ok: {RECORDING_NAME} -> {TRANSCRIPT_PATH}",
        f"link: {RecordingLinks().transcript_url(TRANSCRIPT_PATH)}",
        "button «Протокол встречи»: prt:m:0a1b2c3d",
        "button «Протокол звонка»: prt:c:0a1b2c3d",
    ]


def test_notify_owner_sends_link_and_protocol_callback_buttons(
    caplog: pytest.LogCaptureFixture,
) -> None:
    lines: list[str] = []
    bot = owner_bot()
    outcome = build_check_outcome(console(lines), owner_bot=bot)

    with caplog.at_level(logging.INFO):
        outcome.ready(OWNER_CHAT_ID, TRANSCRIPT)

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
    assert [button.callback_data for button in buttons] == [
        "prt:m:0a1b2c3d",
        "prt:c:0a1b2c3d",
    ]
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
