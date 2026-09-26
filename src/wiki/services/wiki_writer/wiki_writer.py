from contextlib import AbstractContextManager
from pathlib import Path

from src.wiki.errors.wiki_page_exists_error import WikiPageExistsError
from src.wiki.errors.wiki_page_not_found_error import WikiPageNotFoundError
from src.wiki.services.wiki_writer.protocols.i_git_committer import IGitCommitter
from src.wiki.services.wiki_writer.protocols.i_wiki_publisher import IWikiPublisher
from src.wiki.services.wiki_writer.protocols.i_write_path_policy import IWritePathPolicy
from src.wiki.services.wiki_writer.wiki_page_encoding_error import (
    WikiPageEncodingError,
)
from src.wiki.services.wiki_writer.wiki_write_result import WikiWriteResult

COMMIT_PREFIX = "pa: "


class WikiWriter:
    def __init__(
        self,
        lock: AbstractContextManager[object],
        publisher: IWikiPublisher,
        path_policy: IWritePathPolicy,
        git: IGitCommitter,
        author_name: str,
        author_email: str,
    ) -> None:
        self._lock = lock
        self._publisher = publisher
        self._path_policy = path_policy
        self._git = git
        self._author_name = author_name
        self._author_email = author_email

    def create_page(
        self, relative_path: str, content: str, summary: str
    ) -> WikiWriteResult:
        with self._lock:
            self._publisher.refresh()
            file = self._path_policy.resolve_for_write(relative_path)
            if file.exists():
                raise WikiPageExistsError(relative_path)
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text(_with_trailing_newline(content), encoding="utf-8")
            return self._commit_and_publish(file, summary)

    def append_to_page(
        self, relative_path: str, text: str, summary: str
    ) -> WikiWriteResult:
        with self._lock:
            self._publisher.refresh()
            file = self._path_policy.resolve_for_write(relative_path)
            if not file.is_file():
                raise WikiPageNotFoundError(relative_path)
            existing = _read_utf8(file, relative_path)
            separator = "" if not existing or existing.endswith("\n") else "\n"
            file.write_text(
                existing + separator + _with_trailing_newline(text), encoding="utf-8"
            )
            return self._commit_and_publish(file, summary)

    def write_page(
        self, relative_path: str, content: str, summary: str
    ) -> WikiWriteResult:
        with self._lock:
            self._publisher.refresh()
            file = self._path_policy.resolve_for_write(relative_path)
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text(_with_trailing_newline(content), encoding="utf-8")
            return self._commit_and_publish(file, summary)

    def _commit_and_publish(self, file: Path, summary: str) -> WikiWriteResult:
        relative_name = self._path_policy.relative_name(file)
        self._git.run_checked("add", "--", relative_name)
        if not self._git.run_checked(
            "status", "--porcelain", "--", relative_name
        ).strip():
            return WikiWriteResult(
                path=relative_name, changed=False, commit_sha=self._head()
            )
        self._git.run_checked(
            "-c",
            f"user.name={self._author_name}",
            "-c",
            f"user.email={self._author_email}",
            "-c",
            "commit.gpgsign=false",
            "commit",
            "-m",
            _commit_message(summary, relative_name),
        )
        self._publisher.publish()
        return WikiWriteResult(
            path=relative_name, changed=True, commit_sha=self._head()
        )

    def _head(self) -> str:
        return self._git.run_checked("rev-parse", "HEAD").strip()


def _read_utf8(file: Path, relative_path: str) -> str:
    raw = file.read_bytes()
    content = raw.decode("utf-8", errors="replace")
    if content.encode("utf-8") != raw:
        raise WikiPageEncodingError(relative_path)
    return content


def _with_trailing_newline(text: str) -> str:
    return text if text.endswith("\n") else text + "\n"


def _commit_message(summary: str, relative_name: str) -> str:
    one_line = " ".join(summary.split())
    return COMMIT_PREFIX + (one_line or f"правка {relative_name}")
