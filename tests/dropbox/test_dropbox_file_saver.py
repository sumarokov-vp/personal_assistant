from pathlib import Path

import pytest

from src.dropbox.models.journal_action import JournalAction
from src.dropbox.services.boundary.dropbox_access_denied_error import (
    DropboxAccessDeniedError,
)
from src.dropbox.services.boundary.dropbox_boundary import DropboxBoundary
from src.dropbox.services.saver.dropbox_file_saver import DropboxFileSaver
from tests.dropbox.in_memory_dropbox_journal import InMemoryDropboxJournal


@pytest.fixture
def journal() -> InMemoryDropboxJournal:
    return InMemoryDropboxJournal()


@pytest.fixture
def saver(
    boundary: DropboxBoundary, journal: InMemoryDropboxJournal
) -> DropboxFileSaver:
    return DropboxFileSaver(boundary, journal)


def test_save_creates_missing_folder_and_journals_addition(
    saver: DropboxFileSaver, journal: InMemoryDropboxJournal, dropbox_root: Path
):
    path = saver.save("03_home/09_travel/japan_2027", "ticket.pdf", b"ticket")

    assert path == "03_home/09_travel/japan_2027/ticket.pdf"
    assert (dropbox_root / path).read_bytes() == b"ticket"
    assert [(entry.action, entry.target) for entry in journal.entries] == [
        (JournalAction.ADDED, path)
    ]


def test_save_never_overwrites_and_adds_copy_suffix(
    saver: DropboxFileSaver, dropbox_root: Path
):
    folder = "03_home/01_personal_docs"
    original = (dropbox_root / folder / "notes.md").read_bytes()

    second = saver.save(folder, "notes.md", b"new")
    third = saver.save(folder, "notes.md", b"newer")

    assert second == f"{folder}/notes (2).md"
    assert third == f"{folder}/notes (3).md"
    assert (dropbox_root / folder / "notes.md").read_bytes() == original


@pytest.mark.parametrize(
    ("folder", "name"),
    [
        ("Vault", "x.txt"),
        ("01_work/client", "x.txt"),
        ("03_home/07_ecp/egov.kz", "x.txt"),
        ("link_to_vault", "x.txt"),
        ("", "vault_selftest_1"),
        ("03_home", "../escape.txt"),
        ("03_home", ".hidden"),
    ],
)
def test_save_into_closed_place_is_denied(
    saver: DropboxFileSaver, journal: InMemoryDropboxJournal, folder: str, name: str
):
    with pytest.raises(DropboxAccessDeniedError):
        saver.save(folder, name, b"x")
    assert journal.entries == []
