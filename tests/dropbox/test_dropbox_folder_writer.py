from pathlib import Path

import pytest

from src.dropbox.services.boundary.dropbox_access_denied_error import (
    DropboxAccessDeniedError,
)
from src.dropbox.services.boundary.dropbox_boundary import DropboxBoundary
from src.dropbox.services.boundary.dropbox_folder_writer import DropboxFolderWriter

RECORDINGS = "Записи разговоров"


@pytest.fixture
def writer(boundary: DropboxBoundary, dropbox_root: Path) -> DropboxFolderWriter:
    (dropbox_root / RECORDINGS).mkdir()
    return DropboxFolderWriter(boundary=boundary, folder=RECORDINGS)


def test_write_inside_folder_creates_file(
    writer: DropboxFolderWriter, dropbox_root: Path
):
    path = writer.write_new_file(f"{RECORDINGS}/протокол.pdf", b"pdf")

    assert path == f"{RECORDINGS}/протокол.pdf"
    assert (dropbox_root / path).read_bytes() == b"pdf"


def test_repeated_name_gets_copy_number(
    writer: DropboxFolderWriter, dropbox_root: Path
):
    first = writer.write_new_file(f"{RECORDINGS}/протокол.pdf", b"first")
    second = writer.write_new_file(f"{RECORDINGS}/протокол.pdf", b"second")

    assert second == f"{RECORDINGS}/протокол (2).pdf"
    assert (dropbox_root / first).read_bytes() == b"first"
    assert (dropbox_root / second).read_bytes() == b"second"


def test_write_into_subfolder_of_folder_is_allowed(
    writer: DropboxFolderWriter, dropbox_root: Path
):
    path = writer.write_new_file(f"{RECORDINGS}/2026-11/звонок.typ", b"typ")

    assert (dropbox_root / path).read_bytes() == b"typ"


@pytest.mark.parametrize(
    "path",
    [
        "протокол.pdf",
        RECORDINGS,
        "01_work/client/протокол.pdf",
        "Записи разговоров (2)/протокол.pdf",
        "записи разговоров/протокол.pdf",
        f"{RECORDINGS}/../протокол.pdf",
        f"{RECORDINGS}/../01_work/протокол.pdf",
        f"../{RECORDINGS}/протокол.pdf",
        f"/{RECORDINGS}/протокол.pdf",
        f"{RECORDINGS}/link_out/протокол.pdf",
        "Vault/протокол.pdf",
    ],
)
def test_write_outside_folder_is_denied(
    writer: DropboxFolderWriter, dropbox_root: Path, path: str
):
    (dropbox_root / RECORDINGS / "link_out").symlink_to(
        dropbox_root / "01_work", target_is_directory=True
    )
    before = sorted(p.as_posix() for p in dropbox_root.rglob("*"))

    with pytest.raises(DropboxAccessDeniedError):
        writer.write_new_file(path, b"pdf")

    assert sorted(p.as_posix() for p in dropbox_root.rglob("*")) == before


@pytest.mark.parametrize("folder", ["", ".", "..", "../outside"])
def test_folder_outside_dropbox_is_rejected(boundary: DropboxBoundary, folder: str):
    with pytest.raises(ValueError, match="не папка"):
        DropboxFolderWriter(boundary=boundary, folder=folder)
