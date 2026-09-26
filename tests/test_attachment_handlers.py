from types import SimpleNamespace

from unittest.mock import MagicMock

import pytest
from ai_framework import AIApplication, AIResponse, Message, Provider
from ai_framework.attachments import InMemoryAttachmentStore
from ai_framework.infrastructure_factory import InfrastructureContext
from ai_framework.memory.in_memory_store import InMemoryStore
from ai_framework.session.in_memory_session_store import InMemorySessionStore
from bot_framework import BotMessage, BotMessageUser, Role
from bot_framework.domain.role_management.repos import RoleRepo

from src.chat.actions.send_to_agent_action import SendToAgentAction
from src.chat.handlers.attachment_limits import IMAGE_TOO_LARGE_TEXT
from src.chat.handlers.clear_command_handler import ClearCommandHandler
from src.chat.handlers.document_message_handler import (
    FILE_TOO_LARGE_TEXT,
    UNSUPPORTED_FORMAT_TEXT,
    DocumentMessageHandler,
)
from src.chat.handlers.photo_message_handler import PhotoMessageHandler
from tests.test_send_to_agent_action import DatedPromptBuilder, ScriptedProvider

CHAT_ID = 100
USER_ID = 5
THINKING_MESSAGE_ID = 42
MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_IMAGE_BYTES = 5 * 1024 * 1024
# 4 МБ сырых байт — это ~5.3 МБ в base64: больше лимита Claude на картинку
IMAGE_OVER_LIMIT_BYTES = 4 * 1024 * 1024
PDF_BYTES = b"%PDF-1.4 fake"
JPEG_BYTES = b"\xff\xd8\xff\xe0 fake jpeg"


class SessionTrackingProvider(ScriptedProvider):
    def __init__(self, replies: list[AIResponse]) -> None:
        super().__init__(replies)
        self.reset_sessions: list[str] = []

    def reset_session(self, thread_id: str) -> None:
        self.reset_sessions.append(thread_id)


def _ai_application(
    monkeypatch: pytest.MonkeyPatch, provider: ScriptedProvider
) -> AIApplication:
    monkeypatch.setattr(
        "ai_framework.application.create_provider", lambda *_args: provider
    )
    monkeypatch.setattr(
        "ai_framework.application.open_infrastructure",
        lambda _url: InfrastructureContext(
            memory=InMemoryStore(), sessions=InMemorySessionStore()
        ),
    )
    return AIApplication(
        api_key="test",
        provider=Provider.CLAUDE_SDK,
        system_prompt="initial",
        database_url="postgres://unused",
        tools=[],
        history_turns_limit=10,
        attachment_store=InMemoryAttachmentStore(),
    )


def _admin_role_repo() -> MagicMock:
    role_repo = MagicMock(spec=RoleRepo)
    role_repo.get_user_roles.return_value = [Role(id=1, name="admin")]
    return role_repo


def _collaborators(file_bytes: bytes) -> dict[str, MagicMock]:
    downloader = MagicMock()
    downloader.download_document.return_value = file_bytes
    sender = MagicMock()
    sender.send.return_value = BotMessage(
        chat_id=CHAT_ID, message_id=THINKING_MESSAGE_ID, text="thinking"
    )
    return {"downloader": downloader, "sender": sender, "replacer": MagicMock()}


def _action(ai: AIApplication, mocks: dict[str, MagicMock]) -> SendToAgentAction:
    return SendToAgentAction(
        ai=ai,
        system_prompt_builder=DatedPromptBuilder(),
        message_sender=mocks["sender"],
        message_replacer=mocks["replacer"],
        message_deleter=MagicMock(),
    )


def _document_handler(
    ai: AIApplication, mocks: dict[str, MagicMock]
) -> DocumentMessageHandler:
    return DocumentMessageHandler(
        document_downloader=mocks["downloader"],
        send_to_agent_action=_action(ai, mocks),
        message_sender=mocks["sender"],
        message_replacer=mocks["replacer"],
        role_repo=_admin_role_repo(),
        max_file_bytes=MAX_FILE_BYTES,
        max_image_bytes=MAX_IMAGE_BYTES,
    )


def _photo_handler(
    ai: AIApplication, mocks: dict[str, MagicMock]
) -> PhotoMessageHandler:
    return PhotoMessageHandler(
        document_downloader=mocks["downloader"],
        send_to_agent_action=_action(ai, mocks),
        message_sender=mocks["sender"],
        message_replacer=mocks["replacer"],
        role_repo=_admin_role_repo(),
        max_file_bytes=MAX_FILE_BYTES,
        max_image_bytes=MAX_IMAGE_BYTES,
    )


def _document_message(
    file_name: str, mime_type: str, file_size: int, caption: str | None = None
) -> BotMessage:
    message = BotMessage(
        chat_id=CHAT_ID, message_id=1, from_user=BotMessageUser(id=USER_ID)
    )
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


def _photo_message(file_size: int, caption: str | None = None) -> BotMessage:
    message = BotMessage(
        chat_id=CHAT_ID, message_id=1, from_user=BotMessageUser(id=USER_ID)
    )
    message.set_original(
        SimpleNamespace(
            photo=[
                SimpleNamespace(file_id="photo-thumb", file_size=1_000),
                SimpleNamespace(file_id="photo-file", file_size=file_size),
            ],
            caption=caption,
        )
    )
    return message


def _last_user_message(provider: ScriptedProvider) -> Message:
    messages, _system = provider.calls[0]
    return messages[-1]


class TestPhotoAttachment:
    def test_photo_goes_to_assistant_as_jpeg_attachment(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        provider = ScriptedProvider([AIResponse(content="Итого 1250")])
        mocks = _collaborators(JPEG_BYTES)
        with _ai_application(monkeypatch, provider) as ai:
            _photo_handler(ai, mocks).handle(
                _photo_message(len(JPEG_BYTES), caption="сколько тут?")
            )

        mocks["downloader"].download_document.assert_called_once_with("photo-file")
        sent = _last_user_message(provider)
        assert sent.content == "сколько тут?"
        assert sent.attachments is not None
        assert [(a.media_type, a.data) for a in sent.attachments] == [
            ("image/jpeg", JPEG_BYTES)
        ]
        mocks["replacer"].replace.assert_called_once_with(
            chat_id=CHAT_ID, message_id=THINKING_MESSAGE_ID, text="Итого 1250"
        )

    def test_photo_over_image_limit_refused_without_assistant(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        provider = ScriptedProvider([])
        mocks = _collaborators(b"")
        with _ai_application(monkeypatch, provider) as ai:
            _photo_handler(ai, mocks).handle(_photo_message(IMAGE_OVER_LIMIT_BYTES))

        assert provider.calls == []
        mocks["downloader"].download_document.assert_not_called()
        mocks["sender"].send.assert_called_once_with(
            chat_id=CHAT_ID, text=IMAGE_TOO_LARGE_TEXT
        )


class TestDocumentAttachments:
    def test_pdf_goes_to_assistant_as_pdf_attachment(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        provider = ScriptedProvider([AIResponse(content="Счёт на 300")])
        mocks = _collaborators(PDF_BYTES)
        with _ai_application(monkeypatch, provider) as ai:
            _document_handler(ai, mocks).handle(
                _document_message(
                    "invoice.pdf", "application/pdf", len(PDF_BYTES), caption="Что это?"
                )
            )

        sent = _last_user_message(provider)
        assert sent.content == "Что это?\n\nФайл invoice.pdf"
        assert sent.attachments is not None
        assert [(a.media_type, a.filename, a.data) for a in sent.attachments] == [
            ("application/pdf", "invoice.pdf", PDF_BYTES)
        ]
        assert sent.attachments[0].to_content_block()["type"] == "document"

    def test_png_document_goes_to_assistant_as_image_attachment(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        provider = ScriptedProvider([AIResponse(content="Скриншот")])
        mocks = _collaborators(b"\x89PNG fake")
        with _ai_application(monkeypatch, provider) as ai:
            _document_handler(ai, mocks).handle(
                _document_message("screen.png", "image/png", 9)
            )

        sent = _last_user_message(provider)
        assert sent.attachments is not None
        assert [a.media_type for a in sent.attachments] == ["image/png"]
        assert sent.attachments[0].to_content_block()["type"] == "image"

    def test_markdown_goes_to_assistant_as_text(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        provider = ScriptedProvider([AIResponse(content="Три пункта")])
        mocks = _collaborators("# План\n- хлеб".encode())
        with _ai_application(monkeypatch, provider) as ai:
            _document_handler(ai, mocks).handle(
                _document_message("plan.md", "text/markdown", 20, caption="Что тут?")
            )

        messages, _system = provider.calls[0]
        assert [(m.role, m.content, m.attachments) for m in messages] == [
            ("user", "Что тут?\n\nФайл plan.md:\n\n# План\n- хлеб", None)
        ]
        mocks["replacer"].replace.assert_called_once_with(
            chat_id=CHAT_ID, message_id=THINKING_MESSAGE_ID, text="Три пункта"
        )

    def test_unknown_format_refused_without_assistant(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        provider = ScriptedProvider([])
        mocks = _collaborators(b"")
        with _ai_application(monkeypatch, provider) as ai:
            _document_handler(ai, mocks).handle(
                _document_message("book.epub", "application/epub+zip", 100)
            )

        assert provider.calls == []
        mocks["downloader"].download_document.assert_not_called()
        mocks["sender"].send.assert_called_once_with(
            chat_id=CHAT_ID, text=UNSUPPORTED_FORMAT_TEXT
        )

    def test_image_document_over_image_limit_refused_without_assistant(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        provider = ScriptedProvider([])
        mocks = _collaborators(b"")
        with _ai_application(monkeypatch, provider) as ai:
            _document_handler(ai, mocks).handle(
                _document_message("scan.jpg", "image/jpeg", IMAGE_OVER_LIMIT_BYTES)
            )

        assert provider.calls == []
        mocks["downloader"].download_document.assert_not_called()
        mocks["sender"].send.assert_called_once_with(
            chat_id=CHAT_ID, text=IMAGE_TOO_LARGE_TEXT
        )

    def test_pdf_under_general_limit_not_held_to_image_limit(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        pdf_bytes = b"%PDF" + b"0" * IMAGE_OVER_LIMIT_BYTES
        provider = ScriptedProvider([AIResponse(content="Прочитал")])
        mocks = _collaborators(pdf_bytes)
        with _ai_application(monkeypatch, provider) as ai:
            _document_handler(ai, mocks).handle(
                _document_message("big.pdf", "application/pdf", len(pdf_bytes))
            )

        sent = _last_user_message(provider)
        assert sent.attachments is not None
        assert [a.media_type for a in sent.attachments] == ["application/pdf"]

    def test_oversized_file_refused_without_assistant(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        provider = ScriptedProvider([])
        mocks = _collaborators(b"")
        with _ai_application(monkeypatch, provider) as ai:
            _document_handler(ai, mocks).handle(
                _document_message("big.pdf", "application/pdf", MAX_FILE_BYTES + 1)
            )

        assert provider.calls == []
        mocks["downloader"].download_document.assert_not_called()
        mocks["sender"].send.assert_called_once_with(
            chat_id=CHAT_ID, text=FILE_TOO_LARGE_TEXT
        )


class TestClearCommand:
    def test_clear_calls_clear_context_and_resets_sdk_session(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        provider = SessionTrackingProvider(
            [AIResponse(content="Первый"), AIResponse(content="Второй")]
        )
        mocks = _collaborators(b"")
        with _ai_application(monkeypatch, provider) as ai:
            action = _action(ai, mocks)
            action.execute(
                chat_id=CHAT_ID, user_id=USER_ID, text="раз", thinking_message_id=1
            )
            clear_message = BotMessage(
                chat_id=CHAT_ID,
                message_id=2,
                text="/clear",
                from_user=BotMessageUser(id=USER_ID),
            )
            ClearCommandHandler(
                conversation_clearer=ai,
                message_sender=mocks["sender"],
                role_repo=_admin_role_repo(),
            ).handle(clear_message)
            action.execute(
                chat_id=CHAT_ID, user_id=USER_ID, text="два", thinking_message_id=3
            )

        assert provider.reset_sessions == [str(USER_ID)]
        messages, _system = provider.calls[1]
        assert [m.content for m in messages] == ["два"]

    def test_clear_passes_owner_thread_to_clearer(self) -> None:
        clearer = MagicMock()
        sender = MagicMock()
        ClearCommandHandler(
            conversation_clearer=clearer,
            message_sender=sender,
            role_repo=_admin_role_repo(),
        ).handle(
            BotMessage(
                chat_id=CHAT_ID,
                message_id=2,
                text="/clear",
                from_user=BotMessageUser(id=USER_ID),
            )
        )

        clearer.clear_context.assert_called_once_with(str(USER_ID))
