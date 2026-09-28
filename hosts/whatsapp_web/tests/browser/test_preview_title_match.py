from whatsapp_web.browser.services.entities.web_locators import DOCUMENT_PREVIEW_PREFIX
from whatsapp_web.browser.services.web_screen.preview_title_match import (
    PreviewTitleMatch,
)

TITLES = [
    'Просмотреть "Выдуманный отчёт.pdf"',
    'Просмотреть "Выдуманный отчёт.docx"',
    'Просмотреть "Выдуманный отчёт.old.pdf"',
    'Просмотреть "Выдуманный отчёт"',
    'Просмотреть "Другой файл.pdf"',
]


def match(titles: list[str], file_name: str) -> list[int]:
    return PreviewTitleMatch(DOCUMENT_PREVIEW_PREFIX).indexes(titles, file_name)


def test_exact_name_wins_over_names_with_extension():
    assert match(TITLES, "Выдуманный отчёт") == [3]


def test_snapshot_name_without_extension_matches_shown_name_with_one():
    assert match(TITLES[:3], "Выдуманный отчёт") == [0, 1]


def test_full_name_matches_only_itself():
    assert match(TITLES, "Другой файл.pdf") == [4]


def test_unknown_name_matches_nothing():
    assert match(TITLES, "Нет такого") == []
