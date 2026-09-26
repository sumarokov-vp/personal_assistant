from datetime import date
from pathlib import Path

import pytest

from src.memory.models import Deadline
from src.memory.repos import DeadlineRepository, WikiPageStorage
from src.wiki import WikiFactory, WikiPageNotFoundError, WikiPathError, WikiSettings
from tests.wiki.conftest import WikiRemote

DEADLINES = "Assistant/Реестр сроков.md"


def _factory(tmp_path: Path, remote: WikiRemote) -> WikiFactory:
    return WikiFactory(
        WikiSettings(wiki_dir=tmp_path / "bot" / "wiki", remote_url=remote.url)
    )


def test_write_page_creates_missing_page(tmp_path: Path, wiki_remote: WikiRemote):
    writer = _factory(tmp_path, wiki_remote).create_writer()

    result = writer.write_page("Assistant/New.md", "# New", "новая страница")

    assert result.changed
    assert result.commit_sha == wiki_remote.main_head()
    assert wiki_remote.main_file("Assistant/New.md") == "# New\n"


def test_write_page_replaces_whole_page(tmp_path: Path, wiki_remote: WikiRemote):
    writer = _factory(tmp_path, wiki_remote).create_writer()

    result = writer.write_page("Wiki/Existing.md", "# Replaced\n", "замена")

    assert result.changed
    assert wiki_remote.main_file("Wiki/Existing.md") == "# Replaced\n"
    subject = wiki_remote.bare_git().run_checked("log", "-1", "--format=%s", "main")
    assert subject.strip() == "pa: замена"


def test_write_page_with_same_content_makes_no_commit(
    tmp_path: Path, wiki_remote: WikiRemote
):
    writer = _factory(tmp_path, wiki_remote).create_writer()
    head_before = wiki_remote.main_head()

    result = writer.write_page(
        "Wiki/Existing.md", "# Existing\n\nfirst line\n", "то же"
    )

    assert not result.changed
    assert result.commit_sha == head_before
    assert wiki_remote.main_head() == head_before


@pytest.mark.parametrize("relative_path", [".obsidian/x.md", "../x.md", "Wiki/x.txt"])
def test_write_page_respects_path_policy(
    tmp_path: Path, wiki_remote: WikiRemote, relative_path: str
):
    writer = _factory(tmp_path, wiki_remote).create_writer()
    head_before = wiki_remote.main_head()

    with pytest.raises(WikiPathError):
        writer.write_page(relative_path, "x", "попытка")

    assert wiki_remote.main_head() == head_before


def test_memory_upsert_through_wiki_changes_exactly_one_row(
    tmp_path: Path, wiki_remote: WikiRemote
):
    factory = _factory(tmp_path, wiki_remote)
    deadlines = DeadlineRepository(
        WikiPageStorage(
            reader=factory.create_reader(),
            writer=factory.create_writer(),
            page_not_found_error=WikiPageNotFoundError,
        )
    )
    deadlines.upsert(
        Deadline(what="Паспорт РФ", whose="Владимир", expires=date(2026, 3, 1))
    )
    deadlines.upsert(
        Deadline(what="ЭЦП РК", whose="Владимир", expires=date(2027, 1, 5))
    )

    deadlines.upsert(
        Deadline(what="паспорт рф", whose="Владимир", expires=date(2036, 3, 1))
    )

    diff = wiki_remote.bare_git().run_checked(
        "diff", "--unified=0", "main~1", "main", "--", DEADLINES
    )
    changed = [
        line
        for line in diff.splitlines()
        if line[:1] in "+-" and not line.startswith(("+++", "---"))
    ]
    assert len(changed) == 2
    assert "01.03.2026" in changed[0]
    assert "01.03.2036" in changed[1]
    assert "ЭЦП РК" in wiki_remote.main_file(DEADLINES)
