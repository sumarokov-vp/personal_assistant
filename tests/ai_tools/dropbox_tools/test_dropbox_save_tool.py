import json
from pathlib import Path

import pytest
from ai_framework import ToolContext

from src.ai_tools.dropbox_save import DropboxSaveTool
from src.ai_tools.dropbox_save.tool import DropboxSaveInput
from src.dropbox.models.journal_action import JournalAction
from src.dropbox.services.boundary.dropbox_access_policy import DropboxAccessPolicy
from src.dropbox.services.boundary.dropbox_boundary import DropboxBoundary
from src.dropbox.services.saver.dropbox_file_saver import DropboxFileSaver
from src.files.work_folder.work_folder import WorkFolder
from tests.dropbox.in_memory_dropbox_journal import InMemoryDropboxJournal

CONTEXT = ToolContext({"chat_id": 1, "user_id": 7})
TRIP = "03_home/09_travel/thailand_2026-11"
TICKET = b"%PDF-1.4 AirAsia ticket"


@pytest.fixture
def dropbox(tmp_path: Path) -> Path:
    root = tmp_path / "Dropbox"
    (root / "Vault").mkdir(parents=True)
    (root / TRIP).mkdir(parents=True)
    return root


@pytest.fixture
def work_folder(tmp_path: Path) -> WorkFolder:
    return WorkFolder(tmp_path / "work")


@pytest.fixture
def journal() -> InMemoryDropboxJournal:
    return InMemoryDropboxJournal()


@pytest.fixture
def tool(
    dropbox: Path, work_folder: WorkFolder, journal: InMemoryDropboxJournal
) -> DropboxSaveTool:
    boundary = DropboxBoundary(dropbox, DropboxAccessPolicy())
    return DropboxSaveTool(work_folder, DropboxFileSaver(boundary, journal))


def _save(tool: DropboxSaveTool, **arguments: str) -> dict[str, object]:
    result: dict[str, object] = json.loads(
        tool.execute(DropboxSaveInput.model_validate(arguments), CONTEXT)
    )
    return result


def test_mail_pdf_saved_with_same_bytes_and_repeat_gets_copy_suffix(
    tool: DropboxSaveTool,
    work_folder: WorkFolder,
    dropbox: Path,
    journal: InMemoryDropboxJournal,
) -> None:
    ticket = work_folder.put(TICKET, "ticket.pdf", "application/pdf", "mail")

    first = _save(tool, file_id=ticket.id, folder=TRIP)
    second = _save(tool, file_id=ticket.id, folder=TRIP)

    assert first == {"path": f"{TRIP}/ticket.pdf", "renamed": False}
    assert second == {"path": f"{TRIP}/ticket (2).pdf", "renamed": True}
    assert (dropbox / TRIP / "ticket.pdf").read_bytes() == TICKET
    assert (dropbox / TRIP / "ticket (2).pdf").read_bytes() == TICKET
    assert [entry.action for entry in journal.entries] == [JournalAction.ADDED] * 2
    assert [entry.target for entry in journal.entries] == [
        f"{TRIP}/ticket.pdf",
        f"{TRIP}/ticket (2).pdf",
    ]


@pytest.mark.parametrize(
    ("original", "media_type", "requested", "expected"),
    [
        ("ticket.pdf", "application/pdf", "Билет Бангкок", "Билет Бангкок.pdf"),
        ("ticket.pdf", "application/pdf", "Отчёт v1.2", "Отчёт v1.2.pdf"),
        ("scan.JPG", "image/jpeg", "паспорт.jpeg", "паспорт.jpeg"),
        ("file", "image/jpeg", "паспорт", "паспорт.jpg"),
        ("file", "application/pdf", "", "file.pdf"),
    ],
)
def test_requested_name_keeps_or_gets_extension(
    tool: DropboxSaveTool,
    work_folder: WorkFolder,
    original: str,
    media_type: str,
    requested: str,
    expected: str,
) -> None:
    work_file = work_folder.put(b"bytes", original, media_type, "chat")

    result = _save(tool, file_id=work_file.id, folder=TRIP, name=requested)

    assert result["path"] == f"{TRIP}/{expected}"


def test_vault_is_error_and_nothing_written(
    tool: DropboxSaveTool,
    work_folder: WorkFolder,
    dropbox: Path,
    journal: InMemoryDropboxJournal,
) -> None:
    ticket = work_folder.put(TICKET, "ticket.pdf", "application/pdf", "mail")

    result = _save(tool, file_id=ticket.id, folder="Vault/passports")

    assert "error" in result
    assert list((dropbox / "Vault").iterdir()) == []
    assert journal.entries == []


@pytest.mark.parametrize("file_id", ["deadbeef", "../../etc"])
def test_unknown_file_id_is_error(
    tool: DropboxSaveTool,
    dropbox: Path,
    journal: InMemoryDropboxJournal,
    file_id: str,
) -> None:
    result = _save(tool, file_id=file_id, folder=TRIP)

    assert "error" in result
    assert list((dropbox / TRIP).iterdir()) == []
    assert journal.entries == []
