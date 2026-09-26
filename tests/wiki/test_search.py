import threading
from pathlib import Path

import pytest

from src.wiki.search.wiki_searcher import WikiSearcher
from src.wiki.services.wiki_path_policy.wiki_path_policy import WikiPathPolicy
from src.wiki.services.wiki_reader.wiki_reader import WikiReader

PAGES = {
    "Wiki/Проекты/Ассистент.md": (
        "---\ntags: [project]\n---\n# Личный ассистент\n\n"
        "Бот читает вики и пишет заметки.\nЖивёт в colima на Mac mini.\n"
    ),
    "Wiki/Здоровье/Витамины.md": (
        "# Витамины\n\nУтром витамин D, вечером магний.\nАссистент напоминает.\n"
    ),
    "Daily/2026-09-20.md": "Созвон про colima и деплой бота.\n",
    "files/colima-manual.md": "colima start --cpu 4\n",
    ".obsidian/workspace.md": "colima\n",
}


class NoRefresh:
    def refresh(self) -> None:
        pass


@pytest.fixture
def searcher(tmp_path: Path) -> WikiSearcher:
    for relative_path, content in PAGES.items():
        file = tmp_path / relative_path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(content, encoding="utf-8")
    reader = WikiReader(
        wiki_dir=tmp_path,
        lock=threading.Lock(),
        refresher=NoRefresh(),
        path_policy=WikiPathPolicy(tmp_path),
    )
    return WikiSearcher(reader)


def test_finds_page_by_word_from_text_with_path_from_root(searcher: WikiSearcher):
    hits = searcher.search("COLIMA", limit=10)

    assert [hit.path for hit in hits] == [
        "Daily/2026-09-20.md",
        "Wiki/Проекты/Ассистент.md",
    ]
    assistant = hits[1]
    assert assistant.title == "Личный ассистент"
    assert "colima" in assistant.snippet


def test_finds_page_by_part_of_file_name(searcher: WikiSearcher):
    hits = searcher.search("витам", limit=10)

    assert [hit.path for hit in hits] == ["Wiki/Здоровье/Витамины.md"]


def test_name_match_ranks_above_text_match(searcher: WikiSearcher):
    hits = searcher.search("ассистент", limit=10)

    assert [hit.path for hit in hits] == [
        "Wiki/Проекты/Ассистент.md",
        "Wiki/Здоровье/Витамины.md",
    ]


def test_all_words_of_query_must_match(searcher: WikiSearcher):
    assert [hit.path for hit in searcher.search("магний утром", limit=10)] == [
        "Wiki/Здоровье/Витамины.md"
    ]
    assert searcher.search("магний colima", limit=10) == []


def test_limit_cuts_results(searcher: WikiSearcher):
    assert len(searcher.search("colima", limit=1)) == 1
