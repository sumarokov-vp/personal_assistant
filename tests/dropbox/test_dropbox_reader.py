import pytest

from src.dropbox.services.boundary.dropbox_boundary import DropboxBoundary
from src.dropbox.services.reader.dropbox_reader import DropboxReader
from src.dropbox.services.reader.unreadable_format_error import UnreadableFormatError


def test_pdf_text_is_read(boundary: DropboxBoundary):
    text = DropboxReader(boundary).read("Itinerary_ALA_CNX_12-11-2026_000000000000.pdf")

    assert "12.11.2026" in text.text
    assert "CNX" in text.text
    assert not text.truncated


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("03_home/01_personal_docs/passport.txt", "паспорт, срок до 2031"),
        ("03_home/01_personal_docs/notes.md", "# Заметки"),
        ("03_home/01_personal_docs/data.json", '{"a": 1}'),
        ("03_home/01_personal_docs/table.csv", "a,b\n1,2\n"),
    ],
)
def test_text_formats_are_read(boundary: DropboxBoundary, path: str, expected: str):
    assert DropboxReader(boundary).read(path).text == expected


def test_long_text_is_cut_at_ceiling(boundary: DropboxBoundary):
    text = DropboxReader(boundary, max_text_chars=6).read(
        "03_home/01_personal_docs/passport.txt"
    )

    assert text.text == "паспор"
    assert text.truncated


@pytest.mark.parametrize(
    "path",
    ["03_home/01_personal_docs/photo.heic", "scan.pdf", "Apps/HealthFit/ride.fit"],
)
def test_unreadable_format_is_refused(boundary: DropboxBoundary, path: str):
    with pytest.raises(UnreadableFormatError):
        DropboxReader(boundary).read(path)


def test_oversized_pdf_is_refused(boundary: DropboxBoundary):
    with pytest.raises(UnreadableFormatError):
        DropboxReader(boundary, max_pdf_bytes=10).read(
            "Itinerary_ALA_CNX_12-11-2026_000000000000.pdf"
        )


def test_missing_file_is_reported(boundary: DropboxBoundary):
    with pytest.raises(FileNotFoundError):
        DropboxReader(boundary).read("03_home/nothing.txt")
