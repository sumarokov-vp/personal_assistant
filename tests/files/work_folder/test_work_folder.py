from pathlib import Path

import pytest

from src.files.work_folder.work_file_not_found_error import WorkFileNotFoundError
from src.files.work_folder.work_folder import WorkFolder


def test_put_then_get_and_read_return_same_file(tmp_path: Path):
    folder = WorkFolder(tmp_path / "work")

    put = folder.put(b"%PDF-1.7 ticket", "ticket.pdf", "application/pdf", "gmail")

    assert folder.get(put.id) == put
    assert put.name == "ticket.pdf"
    assert put.size == len(b"%PDF-1.7 ticket")
    assert folder.read(put.id) == b"%PDF-1.7 ticket"
    assert (
        tmp_path / "work" / put.id / "ticket.pdf"
    ).read_bytes() == b"%PDF-1.7 ticket"


@pytest.mark.parametrize(
    ("name", "stored"),
    [
        ("../../etc/passwd", "passwd"),
        ("C:\\docs\\scan.png", "scan.png"),
        (".work_file.json", "work_file.json"),
        ("..", "file"),
        ("", "file"),
    ],
)
def test_name_stays_inside_file_directory(tmp_path: Path, name: str, stored: str):
    folder = WorkFolder(tmp_path / "work")

    put = folder.put(b"x", name, "application/octet-stream", "chat")

    assert put.name == stored
    assert folder.read(put.id) == b"x"


@pytest.mark.parametrize("file_id", ["../outside", "a1b2c3d4", "", "A1B2C3D4"])
def test_unknown_or_malformed_id_is_not_found(tmp_path: Path, file_id: str):
    with pytest.raises(WorkFileNotFoundError):
        WorkFolder(tmp_path / "work").get(file_id)
