from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from ai_framework import AIApplication, AIResponse
from bot_framework import BotMessage, BotMessageUser, Role
from bot_framework.domain.role_management.repos import RoleRepo

from src.chat.actions.send_to_agent_action import SendToAgentAction
from src.chat.handlers.document_message_handler import (
    BINARY_ATTACHMENTS_NOT_READY_TEXT,
    FILE_TOO_LARGE_TEXT,
    UNSUPPORTED_FORMAT_TEXT,
    DocumentMessageHandler,
)
from src.chat.handlers.photo_message_handler import (
    PHOTO_NOT_READY_TEXT,
    PhotoMessageHandler,
)
from tests.test_send_to_agent_action import (
    DatedPromptBuilder,
    ScriptedProvider,
    _ai_application,
)

CHAT_ID = 100
THINKING_MESSAGE_ID = 42
MAX_FILE_BYTES = 10 * 1024 * 1024


def _admin_role_repo() -> MagicMock:
    role_repo = MagicMock(spec=RoleRepo)
    role_repo.get_user_roles.return_value = [Role(id=1, name="admin")]
    return role_repo


def _document_message(
    file_name: str, mime_type: str, file_size: int, caption: str | None = None
) -> BotMessage:
    message = BotMessage(chat_id=CHAT_ID, message_id=1, from_user=BotMessageUser(id=5))
    message.set_original(
        SimpleNamespace(
            document=SimpleNamespace(
                file_id="doc-file",
                file_name=file_name,
                mime_type=mime_type,
                file_size=file_size,
            ),
            caption=caption,
        )
    )
    return message


def _document_handler(
    ai: AIApplication, file_bytes: bytes
) -> tuple[DocumentMessageHandler, MagicMock, MagicMock, MagicMock]:
    downloader = MagicMock()
    downloader.download_document.return_value = file_bytes
    sender = MagicMock()
    sender.send.return_value = BotMessage(
        chat_id=CHAT_ID, message_id=THINKING_MESSAGE_ID, text="thinking"
    )
    replacer = MagicMock()
    handler = DocumentMessageHandler(
        document_downloader=downloader,
        send_to_agent_action=SendToAgentAction(
            ai=ai,
            system_prompt_builder=DatedPromptBuilder(),
            message_sender=sender,
            message_replacer=replacer,
            message_deleter=MagicMock(),
        ),
        message_sender=sender,
        message_replacer=replacer,
        role_repo=_admin_role_repo(),
        max_file_bytes=MAX_FILE_BYTES,
    )
    return handler, downloader, sender, replacer


class TestDocumentAttachments:
    def test_markdown_goes_to_assistant_as_text(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        provider = ScriptedProvider([AIResponse(content="Три пункта")])
        with _ai_application(monkeypatch, provider) as ai:
            handler, _downloader, _sender, replacer = _document_handler(
                ai, "# План\n- хлеб".encode()
            )
            handler.handle(
                _document_message("plan.md", "text/markdown", 20, caption="Что тут?")
            )

        messages, _system = provider.calls[0]
        assert [(m.role, m.content) for m in messages] == [
            ("user", "Что тут?\n\nФайл plan.md:\n\n# План\n- хлеб")
        ]
        replacer.replace.assert_called_once_with(
            chat_id=CHAT_ID, message_id=THINKING_MESSAGE_ID, text="Три пункта"
        )

    def test_unknown_format_refused_without_assistant(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        provider = ScriptedProvider([])
        with _ai_application(monkeypatch, provider) as ai:
            handler, downloader, sender, _replacer = _document_handler(ai, b"")
            handler.handle(_document_message("book.epub", "application/epub+zip", 100))

        assert provider.calls == []
        downloader.download_document.assert_not_called()
        sender.send.assert_called_once_with(
            chat_id=CHAT_ID, text=UNSUPPORTED_FORMAT_TEXT
        )

    def test_oversized_file_refused_without_assistant(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        provider = ScriptedProvider([])
        with _ai_application(monkeypatch, provider) as ai:
            handler, downloader, sender, _replacer = _document_handler(ai, b"")
            handler.handle(
                _document_message("big.txt", "text/plain", MAX_FILE_BYTES + 1)
            )

        assert provider.calls == []
        downloader.download_document.assert_not_called()
        sender.send.assert_called_once_with(chat_id=CHAT_ID, text=FILE_TOO_LARGE_TEXT)

    def test_pdf_temporarily_refused_without_assistant(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        provider = ScriptedProvider([])
        with _ai_application(monkeypatch, provider) as ai:
            handler, downloader, sender, _replacer = _document_handler(ai, b"")
            handler.handle(_document_message("check.pdf", "application/pdf", 1000))

        assert provider.calls == []
        downloader.download_document.assert_not_called()
        sender.send.assert_called_once_with(
            chat_id=CHAT_ID, text=BINARY_ATTACHMENTS_NOT_READY_TEXT
        )


class TestPhotoAttachment:
    def test_photo_temporarily_refused_without_assistant(self) -> None:
        sender = MagicMock()
        handler = PhotoMessageHandler(
            message_sender=sender,
            role_repo=_admin_role_repo(),
            max_file_bytes=MAX_FILE_BYTES,
        )
        message = BotMessage(
            chat_id=CHAT_ID, message_id=1, from_user=BotMessageUser(id=5)
        )
        message.set_original(
            SimpleNamespace(
                photo=[SimpleNamespace(file_id="photo-file", file_size=50_000)],
                caption="сколько тут?",
            )
        )

        handler.handle(message)

        sender.send.assert_called_once_with(chat_id=CHAT_ID, text=PHOTO_NOT_READY_TEXT)
