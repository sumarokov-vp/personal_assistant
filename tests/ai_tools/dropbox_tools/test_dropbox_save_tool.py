import json
from pathlib import Path

import pytest
from ai_framework import Attachment
from ai_framework.attachments.in_memory_attachment_store import InMemoryAttachmentStore
from ai_framework.entities.attachment import AttachmentMediaType
from ai_framework.entities.message import Message
from ai_framework.entities.tool import ToolResult
from ai_framework.entities.tool_context import ToolContext

from src.ai_tools.dropbox_save import ChatAttachments, DropboxSaveTool
from src.ai_tools.dropbox_save.tool import DropboxSaveInput
from src.dropbox.models.journal_action import JournalAction
from src.dropbox.services.boundary.dropbox_access_policy import DropboxAccessPolicy
from src.dropbox.services.boundary.dropbox_boundary import DropboxBoundary
from src.dropbox.services.saver.dropbox_file_saver import DropboxFileSaver
from tests.dropbox.in_memory_dropbox_journal import InMemoryDropboxJournal

OWNER_ID = 7
CONTEXT = ToolContext({"chat_id": 1, "user_id": OWNER_ID})
TRIP = "03_home/09_travel/thailand_2026-11"
TICKET = b"%PDF-1.4 ticket"


class InMemoryHistory:
    def __init__(self) -> None:
        self.messages: list[Message] = []

    def get_messages(self, thread_id: str) -> list[Message]:
        assert thread_id == str(OWNER_ID)
        return self.messages


class Chat:
    def __init__(self, turns_limit: int = 10) -> None:
        self.history = InMemoryHistory()
        self.store = InMemoryAttachmentStore()
        self.attachments = ChatAttachments(self.history, self.store, turns_limit)

    def send(
        self, text: str, files: list[tuple[str | None, AttachmentMediaType, bytes]]
    ) -> None:
        stored = [
            Attachment(
                media_type=media_type,
                filename=filename,
                key=self.store.put(data, media_type),
            )
            for filename, media_type, data in files
        ]
        self.history.messages.append(
            Message(role="user", content=text, attachments=stored or None)
        )

    def tool_round(self) -> None:
        self.history.messages.append(Message(role="assistant", content=""))
        self.history.messages.append(
            Message(
                role="user",
                content="",
                tool_results=[ToolResult(tool_call_id="1", content="{}")],
            )
        )


@pytest.fixture
def dropbox(tmp_path: Path) -> Path:
    (tmp_path / "Vault").mkdir()
    (tmp_path / TRIP).mkdir(parents=True)
    return tmp_path


@pytest.fixture
def journal() -> InMemoryDropboxJournal:
    return InMemoryDropboxJournal()


def _tool(
    chat: Chat, dropbox: Path, journal: InMemoryDropboxJournal
) -> DropboxSaveTool:
    boundary = DropboxBoundary(dropbox, DropboxAccessPolicy())
    return DropboxSaveTool(chat.attachments, DropboxFileSaver(boundary, journal))


def _save(tool: DropboxSaveTool, **arguments: str) -> dict[str, object]:
    result: dict[str, object] = json.loads(
        tool.execute(DropboxSaveInput.model_validate(arguments), CONTEXT)
    )
    return result


def test_pdf_goes_to_trip_folder_and_repeat_gets_copy_suffix(
    dropbox: Path, journal: InMemoryDropboxJournal
) -> None:
    chat = Chat()
    chat.send("Файл ticket.pdf", [("ticket.pdf", "application/pdf", TICKET)])
    tool = _tool(chat, dropbox, journal)

    first = _save(tool, folder=TRIP)
    chat.send("Файл ticket.pdf", [("ticket.pdf", "application/pdf", b"%PDF again")])
    second = _save(tool, folder=TRIP)

    assert first == {"path": f"{TRIP}/ticket.pdf", "renamed": False}
    assert second == {"path": f"{TRIP}/ticket (2).pdf", "renamed": True}
    assert (dropbox / TRIP / "ticket.pdf").read_bytes() == TICKET
    assert [entry.action for entry in journal.entries] == [JournalAction.ADDED] * 2


def test_picks_earlier_attachment_by_name_across_tool_rounds(
    dropbox: Path, journal: InMemoryDropboxJournal
) -> None:
    chat = Chat()
    chat.send("Файл visa.pdf", [("visa.pdf", "application/pdf", b"visa")])
    chat.tool_round()
    chat.send("Файл hotel.pdf", [("hotel.pdf", "application/pdf", b"hotel")])
    chat.tool_round()
    chat.send("положи визу в Таиланд", [])

    result = _save(
        _tool(chat, dropbox, journal), folder=TRIP, attachment_filename="VISA.pdf"
    )

    assert result["path"] == f"{TRIP}/visa.pdf"
    assert (dropbox / TRIP / "visa.pdf").read_bytes() == b"visa"


def test_attachment_older_than_history_window_is_not_found(
    dropbox: Path, journal: InMemoryDropboxJournal
) -> None:
    chat = Chat(turns_limit=2)
    chat.send("Файл old.pdf", [("old.pdf", "application/pdf", b"old")])
    chat.send("привет", [])
    chat.send("положи файл", [])

    result = _save(_tool(chat, dropbox, journal), folder=TRIP)

    assert "error" in result
    assert list((dropbox / TRIP).iterdir()) == []


@pytest.mark.parametrize(
    ("filename", "media_type", "requested", "expected"),
    [
        ("ticket.pdf", "application/pdf", "Билет Бангкок", "Билет Бангкок.pdf"),
        ("ticket.pdf", "application/pdf", "Отчёт v1.2", "Отчёт v1.2.pdf"),
        ("scan.JPG", "image/jpeg", "паспорт.jpeg", "паспорт.jpeg"),
        (None, "image/jpeg", "паспорт", "паспорт.jpg"),
    ],
)
def test_requested_name_keeps_or_gets_extension(
    dropbox: Path,
    journal: InMemoryDropboxJournal,
    filename: str | None,
    media_type: AttachmentMediaType,
    requested: str,
    expected: str,
) -> None:
    chat = Chat()
    chat.send("фото", [(filename, media_type, b"bytes")])

    result = _save(_tool(chat, dropbox, journal), folder=TRIP, name=requested)

    assert result["path"] == f"{TRIP}/{expected}"


def test_closed_folder_is_error_and_nothing_written(
    dropbox: Path, journal: InMemoryDropboxJournal
) -> None:
    chat = Chat()
    chat.send("Файл ticket.pdf", [("ticket.pdf", "application/pdf", TICKET)])

    result = _save(_tool(chat, dropbox, journal), folder="Vault")

    assert "error" in result
    assert list((dropbox / "Vault").iterdir()) == []
    assert journal.entries == []
