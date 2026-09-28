from datetime import UTC, datetime
from pathlib import Path

import pytest
from bot_framework import ParseMode

from src.agent_notifications.services.delivery import AgentNotificationDelivery
from src.agent_notifications.services.dropbox_file_store import DropboxAgentFileStore
from src.agent_notifications.services.entities import (
    DeliveryOutcome,
    IncomingAttachment,
    IncomingNotification,
)
from src.agent_notifications.services.text_splitter import TelegramTextSplitter
from src.dropbox.services.boundary.dropbox_access_policy import DropboxAccessPolicy
from src.dropbox.services.boundary.dropbox_boundary import DropboxBoundary
from tests.agent_notifications.in_memory_notification_journal import (
    InMemoryNotificationJournal,
)
from tests.agent_notifications.recording_document_sender import (
    RecordingDocumentSender,
)
from tests.agent_notifications.recording_message_sender import RecordingMessageSender

OWNER_CHAT_ID = 42
PDF = b"%PDF-1.7 " + b"x" * 1250
AGENTS_PATH = "Personal Assistant/agents/big.pdf"


@pytest.fixture
def dropbox_root(tmp_path: Path) -> Path:
    root = tmp_path / "dropbox"
    (root / "Personal Assistant" / "agents").mkdir(parents=True)
    return root


@pytest.fixture
def journal() -> InMemoryNotificationJournal:
    return InMemoryNotificationJournal()


@pytest.fixture
def messages() -> RecordingMessageSender:
    return RecordingMessageSender()


@pytest.fixture
def documents() -> RecordingDocumentSender:
    return RecordingDocumentSender()


def build_delivery(
    journal: InMemoryNotificationJournal,
    messages: RecordingMessageSender,
    documents: RecordingDocumentSender,
    dropbox_root: Path | None,
) -> AgentNotificationDelivery:
    return AgentNotificationDelivery(
        journal=journal,
        message_sender=messages,
        document_sender=documents,
        splitter=TelegramTextSplitter(),
        owner_chat_id=OWNER_CHAT_ID,
        file_store=(
            DropboxAgentFileStore(
                dropbox=DropboxBoundary(
                    root=dropbox_root, policy=DropboxAccessPolicy()
                ),
                size_limit_bytes=50 * 1024 * 1024,
            )
            if dropbox_root is not None
            else None
        ),
    )


@pytest.fixture
def delivery(
    journal: InMemoryNotificationJournal,
    messages: RecordingMessageSender,
    documents: RecordingDocumentSender,
    dropbox_root: Path,
) -> AgentNotificationDelivery:
    return build_delivery(journal, messages, documents, dropbox_root)


def file_notification(
    filename: str | None = "report.pdf",
    content: bytes = PDF,
    path: str | None = None,
    declared_size: int | None = None,
    caption: str = "",
) -> IncomingNotification:
    return IncomingNotification(
        message_id="f-1",
        sender="agent-mac-mini",
        body=caption,
        published_at=datetime(2026, 9, 28, 9, 0, tzinfo=UTC),
        attachment=IncomingAttachment(
            filename=filename,
            content=content,
            path=path,
            declared_size=declared_size,
        ),
    )


def test_file_from_body_goes_as_document_after_source_line(
    delivery: AgentNotificationDelivery,
    journal: InMemoryNotificationJournal,
    messages: RecordingMessageSender,
    documents: RecordingDocumentSender,
) -> None:
    outcome = delivery.deliver(file_notification(caption="отчёт за сентябрь"))

    assert outcome is DeliveryOutcome.DELIVERED
    assert [(m.chat_id, m.text, m.parse_mode) for m in messages.sent] == [
        (
            OWNER_CHAT_ID,
            "Агент mac-mini: файл report.pdf (1,2 КБ)\nотчёт за сентябрь",
            ParseMode.PLAIN,
        )
    ]
    assert [(d.chat_id, d.document, d.filename) for d in documents.sent] == [
        (OWNER_CHAT_ID, PDF, "report.pdf")
    ]
    stored = journal.notifications["f-1"]
    assert (stored.file_name, stored.file_size, stored.body) == (
        "report.pdf",
        len(PDF),
        "отчёт за сентябрь",
    )
    assert stored.delivered_at is not None


def test_file_by_path_is_read_from_dropbox_and_sent_as_document(
    delivery: AgentNotificationDelivery,
    journal: InMemoryNotificationJournal,
    messages: RecordingMessageSender,
    documents: RecordingDocumentSender,
    dropbox_root: Path,
) -> None:
    (dropbox_root / AGENTS_PATH).write_bytes(PDF)

    outcome = delivery.deliver(
        file_notification(
            filename="big.pdf", content=b"", path=AGENTS_PATH, declared_size=len(PDF)
        )
    )

    assert outcome is DeliveryOutcome.DELIVERED
    assert [m.text for m in messages.sent] == ["Агент mac-mini: файл big.pdf (1,2 КБ)"]
    assert [(d.document, d.filename) for d in documents.sent] == [(PDF, "big.pdf")]
    stored = journal.notifications["f-1"]
    assert (stored.file_name, stored.file_size, stored.body) == (
        "big.pdf",
        len(PDF),
        "",
    )


def test_repeated_delivered_file_is_not_sent_twice(
    delivery: AgentNotificationDelivery,
    messages: RecordingMessageSender,
    documents: RecordingDocumentSender,
) -> None:
    delivery.deliver(file_notification())

    outcome = delivery.deliver(file_notification())

    assert outcome is DeliveryOutcome.ALREADY_DELIVERED
    assert len(messages.sent) == 1
    assert len(documents.sent) == 1


def test_vanished_file_is_reported_to_owner_as_text(
    delivery: AgentNotificationDelivery,
    journal: InMemoryNotificationJournal,
    messages: RecordingMessageSender,
    documents: RecordingDocumentSender,
) -> None:
    outcome = delivery.deliver(
        file_notification(
            filename="big.pdf", content=b"", path=AGENTS_PATH, declared_size=20 * 2**20
        )
    )

    assert outcome is DeliveryOutcome.DELIVERED
    assert [m.text for m in messages.sent] == [
        "Агент mac-mini: файл big.pdf (20 МБ) не дошёл — в Dropbox его уже нет"
    ]
    assert documents.sent == []
    stored = journal.notifications["f-1"]
    assert (stored.file_name, stored.file_size) == ("big.pdf", 20 * 2**20)
    assert stored.delivered_at is not None


@pytest.mark.parametrize("filename", [None, "", "  "])
def test_file_without_filename_is_rejected(
    delivery: AgentNotificationDelivery,
    journal: InMemoryNotificationJournal,
    messages: RecordingMessageSender,
    documents: RecordingDocumentSender,
    filename: str | None,
) -> None:
    outcome = delivery.deliver(file_notification(filename=filename))

    assert outcome is DeliveryOutcome.REJECTED
    assert journal.notifications == {}
    assert messages.sent == []
    assert documents.sent == []


def test_file_by_path_is_rejected_without_dropbox(
    journal: InMemoryNotificationJournal,
    messages: RecordingMessageSender,
    documents: RecordingDocumentSender,
) -> None:
    delivery = build_delivery(journal, messages, documents, dropbox_root=None)

    outcome = delivery.deliver(file_notification(content=b"", path=AGENTS_PATH))

    assert outcome is DeliveryOutcome.REJECTED
    assert journal.notifications == {}
    assert messages.sent == []


@pytest.mark.parametrize(
    "path",
    [
        "Personal Assistant/big.pdf",
        "Documents/big.pdf",
        "Personal Assistant/agents",
        "Personal Assistant/agents/../secret.pdf",
    ],
)
def test_file_by_refused_path_is_rejected(
    delivery: AgentNotificationDelivery,
    journal: InMemoryNotificationJournal,
    messages: RecordingMessageSender,
    documents: RecordingDocumentSender,
    dropbox_root: Path,
    path: str,
) -> None:
    (dropbox_root / "Personal Assistant" / "secret.pdf").write_bytes(PDF)

    outcome = delivery.deliver(file_notification(content=b"", path=path))

    assert outcome is DeliveryOutcome.REJECTED
    assert journal.notifications == {}
    assert messages.sent == []
    assert documents.sent == []
