import threading
from collections.abc import Callable
from pathlib import Path

import pytest

from src.wiki import (
    WikiFactory,
    WikiPageChangedError,
    WikiPathError,
    WikiSettings,
    WikiWriter,
)
from src.wiki.repos.git_cli import GitCli
from src.wiki.services.wiki_path_policy.wiki_path_policy import WikiPathPolicy
from src.wiki.services.wiki_sync.wiki_sync import WikiSync
from tests.wiki.conftest import WikiRemote


class GitWithRaceBeforeFirstPush:
    def __init__(self, inner: GitCli, race: Callable[[], None]) -> None:
        self._inner = inner
        self._race = race
        self._raced = False

    def run_checked(self, *args: str, cwd: Path | None = None) -> str:
        return self._inner.run_checked(*args, cwd=cwd)

    def succeeds(self, *args: str, cwd: Path | None = None) -> bool:
        if args[:1] == ("push",) and not self._raced:
            self._raced = True
            self._race()
        return self._inner.succeeds(*args, cwd=cwd)


def _settings(tmp_path: Path, remote: WikiRemote) -> WikiSettings:
    return WikiSettings(wiki_dir=tmp_path / "bot" / "wiki", remote_url=remote.url)


def _writer_with_race(
    tmp_path: Path, remote: WikiRemote, race: Callable[[], None]
) -> WikiWriter:
    settings = _settings(tmp_path, remote)
    git = GitWithRaceBeforeFirstPush(GitCli(settings.wiki_dir), race)
    sync = WikiSync(git=git, wiki_dir=settings.wiki_dir, remote_url=settings.remote_url)
    return WikiWriter(
        lock=threading.Lock(),
        publisher=sync,
        path_policy=WikiPathPolicy(settings.wiki_dir),
        git=git,
        author_name=settings.author_name,
        author_email=settings.author_email,
    )


def test_created_page_reaches_bare_main(tmp_path: Path, wiki_remote: WikiRemote):
    factory = WikiFactory(_settings(tmp_path, wiki_remote))

    result = factory.create_writer().create_page(
        "Wiki/Note.md", "hello", "заметка о встрече"
    )

    assert result.changed
    assert result.commit_sha == wiki_remote.main_head()
    assert wiki_remote.main_file("Wiki/Note.md") == "hello\n"
    author_and_subject = wiki_remote.bare_git().run_checked(
        "log", "-1", "--format=%an|%s", "main"
    )
    assert author_and_subject.strip() == "Personal Assistant|pa: заметка о встрече"


def test_reader_sees_owner_changes_after_pull(tmp_path: Path, wiki_remote: WikiRemote):
    reader = WikiFactory(_settings(tmp_path, wiki_remote)).create_reader()
    assert reader.read_page("Wiki/Existing.md").content == "# Existing\n\nfirst line\n"

    wiki_remote.owner_commit("Wiki/Fresh.md", "fresh\n", "owner adds page")

    assert reader.read_page("Wiki/Fresh.md").content == "fresh\n"
    assert [page.path for page in reader.read_all_pages()] == [
        "Wiki/Existing.md",
        "Wiki/Fresh.md",
    ]


def test_rejected_push_is_rebased_and_retried(tmp_path: Path, wiki_remote: WikiRemote):
    owner_commits: list[str] = []
    writer = _writer_with_race(
        tmp_path,
        wiki_remote,
        lambda: owner_commits.append(
            wiki_remote.owner_commit(
                "Wiki/Other.md", "other\n", "owner edits other page"
            )
        ),
    )

    result = writer.append_to_page("Wiki/Existing.md", "bot line", "дописал строку")

    assert result.commit_sha == wiki_remote.main_head()
    assert wiki_remote.main_file("Wiki/Other.md") == "other\n"
    assert wiki_remote.main_file("Wiki/Existing.md").endswith("first line\nbot line\n")
    parent = wiki_remote.bare_git().run_checked("rev-parse", "main~1").strip()
    assert parent == owner_commits[0]


def test_conflict_keeps_owner_commit_and_reports_retry(
    tmp_path: Path, wiki_remote: WikiRemote
):
    owner_commits: list[str] = []
    owner_content = "# Existing\n\nfirst line\nowner line\n"
    writer = _writer_with_race(
        tmp_path,
        wiki_remote,
        lambda: owner_commits.append(
            wiki_remote.owner_commit("Wiki/Existing.md", owner_content, "owner appends")
        ),
    )

    with pytest.raises(WikiPageChangedError):
        writer.append_to_page("Wiki/Existing.md", "bot line", "дописал строку")

    assert wiki_remote.main_head() == owner_commits[0]
    assert wiki_remote.main_file("Wiki/Existing.md") == owner_content
    bot_git = GitCli(tmp_path / "bot" / "wiki")
    assert bot_git.run_checked("rev-parse", "HEAD").strip() == owner_commits[0]
    assert bot_git.run_checked("status", "--porcelain") == ""


@pytest.mark.parametrize(
    "relative_path",
    [
        ".obsidian/x.md",
        ".obsidian/app.json",
        ".git/config",
        "Wiki/.git/x.md",
        "../x.md",
        "Wiki/../../x.md",
        "/etc/x.md",
        "Wiki/note.txt",
        "",
    ],
)
def test_write_outside_allowed_pages_is_rejected(
    tmp_path: Path, wiki_remote: WikiRemote, relative_path: str
):
    writer = WikiFactory(_settings(tmp_path, wiki_remote)).create_writer()
    head_before = wiki_remote.main_head()

    with pytest.raises(WikiPathError):
        writer.create_page(relative_path, "x", "попытка")

    assert wiki_remote.main_head() == head_before
    assert not (tmp_path / "x.md").exists()


@pytest.mark.parametrize(
    "relative_path", [".git/config", ".obsidian/app.json", "../owner/Wiki/Existing.md"]
)
def test_read_outside_wiki_is_rejected(
    tmp_path: Path, wiki_remote: WikiRemote, relative_path: str
):
    reader = WikiFactory(_settings(tmp_path, wiki_remote)).create_reader()

    with pytest.raises(WikiPathError):
        reader.read_page(relative_path)


def test_symlink_leading_outside_is_rejected(tmp_path: Path, wiki_remote: WikiRemote):
    outside = tmp_path / "outside"
    outside.mkdir()
    wiki_remote.owner_symlink("Wiki/escape", outside)
    factory = WikiFactory(_settings(tmp_path, wiki_remote))

    with pytest.raises(WikiPathError):
        factory.create_writer().create_page("Wiki/escape/x.md", "x", "попытка")
    with pytest.raises(WikiPathError):
        factory.create_reader().read_page("Wiki/escape/secret.md")
    assert list(outside.iterdir()) == []
