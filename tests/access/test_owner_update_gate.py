import logging
from typing import Any
from unittest.mock import Mock

import pytest
from telebot import TeleBot
from telebot.handler_backends import BaseMiddleware
from telebot.types import CallbackQuery, Message, Update

from src.access.services.owner_gate import OwnerUpdateGate
from src.access.services.update_gate_installer import UpdateGateInstaller

OWNER_ID = 111
STRANGER_ID = 222
GROUP_CHAT_ID = -1001
PRIVATE_CONTENT = "секретное содержимое"
UNREACHABLE_BOT = "1:test"
GATE_LOGGER = "src.access.services.owner_gate.owner_update_gate"


class EnsureUserSpy(BaseMiddleware):
    def __init__(self) -> None:
        super().__init__()
        self.update_types = ["message", "callback_query"]
        self.seen: list[Any] = []

    def pre_process(self, message: Any, data: Any) -> None:
        self.seen.append(message)

    def post_process(self, message: Any, data: Any, exception: Any) -> None:
        return None


class GatedBot:
    def __init__(self) -> None:
        self.bot = TeleBot(UNREACHABLE_BOT, threaded=False, use_class_middlewares=True)
        self.send_message = Mock()
        self.handled: list[str] = []
        self.ensure_user = EnsureUserSpy()
        self.bot.setup_middleware(self.ensure_user)
        self._register_handlers()
        UpdateGateInstaller(OwnerUpdateGate(OWNER_ID)).install(self.bot)

    def _register_handlers(self) -> None:
        for name in ("start", "request_role"):
            self.bot.register_message_handler(
                self._message_handler(name), commands=[name]
            )
        for name in ("voice", "photo", "document", "text"):
            self.bot.register_message_handler(
                self._message_handler(name), content_types=[name]
            )
        self.bot.register_callback_query_handler(
            self._callback_handler, func=lambda _: True
        )

    def _message_handler(self, name: str) -> Any:
        def handle(message: Message) -> None:
            self.handled.append(name)
            self.send_message(message.chat.id, name)

        return handle

    def _callback_handler(self, callback: CallbackQuery) -> None:
        self.handled.append("callback")
        self.send_message(callback.from_user.id, "callback")

    def feed(self, update: Update) -> None:
        self.bot.process_new_updates([update])


def user(user_id: int) -> dict[str, Any]:
    return {"id": user_id, "is_bot": False, "first_name": "x"}


def private_chat(user_id: int) -> dict[str, Any]:
    return {"id": user_id, "type": "private"}


def group_chat() -> dict[str, Any]:
    return {"id": GROUP_CHAT_ID, "type": "supergroup", "title": "g"}


def message(sender_id: int, chat: dict[str, Any], **content: Any) -> dict[str, Any]:
    return {
        "message_id": 1,
        "date": 0,
        "chat": chat,
        "from": user(sender_id),
        **content,
    }


def command(name: str) -> dict[str, Any]:
    text = f"/{name}"
    return {
        "text": text,
        "entities": [{"type": "bot_command", "offset": 0, "length": len(text)}],
    }


CONTENTS: dict[str, dict[str, Any]] = {
    "text": {"text": PRIVATE_CONTENT},
    "voice": {"voice": {"file_id": "v", "file_unique_id": "v", "duration": 1}},
    "photo": {
        "photo": [{"file_id": "p", "file_unique_id": "p", "width": 1, "height": 1}],
        "caption": PRIVATE_CONTENT,
    },
    "document": {
        "document": {"file_id": "d", "file_unique_id": "d"},
        "caption": PRIVATE_CONTENT,
    },
    "start": command("start"),
    "request_role": command("request_role"),
}


def message_update(sender_id: int, chat: dict[str, Any], kind: str) -> Update:
    return Update.de_json(
        {"update_id": 10, "message": message(sender_id, chat, **CONTENTS[kind])}
    )


def callback_update(sender_id: int, chat: dict[str, Any]) -> Update:
    return Update.de_json(
        {
            "update_id": 10,
            "callback_query": {
                "id": "c",
                "from": user(sender_id),
                "chat_instance": "i",
                "data": PRIVATE_CONTENT,
                "message": message(OWNER_ID, chat, text="card"),
            },
        }
    )


def stranger_updates() -> list[tuple[str, Update]]:
    updates = [
        (kind, message_update(STRANGER_ID, private_chat(STRANGER_ID), kind))
        for kind in CONTENTS
    ]
    updates.append(
        ("callback", callback_update(STRANGER_ID, private_chat(STRANGER_ID)))
    )
    updates.append(("owner_in_group", message_update(OWNER_ID, group_chat(), "text")))
    updates.append(("owner_callback_in_group", callback_update(OWNER_ID, group_chat())))
    return updates


@pytest.mark.parametrize(
    ("case", "update"), stranger_updates(), ids=[c for c, _ in stranger_updates()]
)
def test_foreign_update_is_dropped_silently(
    case: str, update: Update, caplog: pytest.LogCaptureFixture
) -> None:
    gated = GatedBot()

    with caplog.at_level(logging.INFO, logger=GATE_LOGGER):
        gated.feed(update)

    assert gated.handled == []
    assert gated.ensure_user.seen == []
    gated.send_message.assert_not_called()
    records = [r for r in caplog.records if r.name == GATE_LOGGER]
    assert len(records) == 1
    line = records[0].getMessage()
    assert PRIVATE_CONTENT not in line
    assert "file_id" not in line
    assert gated.bot.last_update_id == update.update_id


def test_log_line_names_type_sender_and_chat(caplog: pytest.LogCaptureFixture) -> None:
    gated = GatedBot()

    with caplog.at_level(logging.INFO, logger=GATE_LOGGER):
        gated.feed(message_update(OWNER_ID, group_chat(), "text"))

    assert caplog.records[-1].getMessage() == (
        f"Dropped update: type=message from={OWNER_ID} chat={GROUP_CHAT_ID}"
    )


def test_inline_query_is_dropped() -> None:
    gated = GatedBot()
    gated.bot.register_inline_handler(Mock(), func=lambda _: True)

    gated.feed(
        Update.de_json(
            {
                "update_id": 11,
                "inline_query": {
                    "id": "q",
                    "from": user(OWNER_ID),
                    "query": PRIVATE_CONTENT,
                    "offset": "",
                },
            }
        )
    )

    assert gated.handled == []


@pytest.mark.parametrize("kind", list(CONTENTS))
def test_owner_message_in_private_chat_reaches_handler(kind: str) -> None:
    gated = GatedBot()

    gated.feed(message_update(OWNER_ID, private_chat(OWNER_ID), kind))

    assert gated.handled == [kind]
    assert len(gated.ensure_user.seen) == 1
    gated.send_message.assert_called_once()


def test_owner_callback_in_private_chat_reaches_handler() -> None:
    gated = GatedBot()

    gated.feed(callback_update(OWNER_ID, private_chat(OWNER_ID)))

    assert gated.handled == ["callback"]
    assert len(gated.ensure_user.seen) == 1
