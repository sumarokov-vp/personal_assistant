import unicodedata
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

from src.dropbox.services.search.protocols.i_dropbox_directory_boundary import (
    IDropboxDirectoryBoundary,
)
from src.dropbox.services.search.search_hit import SearchHit
from src.dropbox.services.search.search_result import SearchResult


class DropboxSearch:
    def __init__(self, boundary: IDropboxDirectoryBoundary) -> None:
        self._boundary = boundary

    def find(self, query: str, limit: int = 30, within: str = "") -> SearchResult:
        words = _normalize(query).split()
        if not words:
            raise ValueError(
                "Пустой запрос: назови хотя бы одно слово из имени или пути"
            )
        matches = [
            entry
            for entry in self._walk(self._boundary.resolve(within))
            if all(word in _normalize(self._boundary.relative(entry)) for word in words)
        ]
        matches.sort(key=lambda entry: self._rank(entry, words))
        return SearchResult(
            query=query,
            hits=[self._hit(entry) for entry in matches[:limit]],
            total=len(matches),
        )

    def _walk(self, directory: Path) -> Iterator[Path]:
        for child in self._boundary.visible_children(directory):
            yield child
            if child.is_dir() and not child.is_symlink():
                yield from self._walk(child)

    def _rank(self, entry: Path, words: list[str]) -> tuple[bool, int, str]:
        relative = self._boundary.relative(entry)
        name_matches_all = all(word in _normalize(entry.name) for word in words)
        return not name_matches_all, relative.count("/"), relative.casefold()

    def _hit(self, entry: Path) -> SearchHit:
        status = entry.stat()
        return SearchHit(
            path=self._boundary.relative(entry),
            is_folder=entry.is_dir(),
            size=0 if entry.is_dir() else status.st_size,
            modified_at=datetime.fromtimestamp(status.st_mtime, tz=UTC),
        )


def _normalize(text: str) -> str:
    return unicodedata.normalize("NFC", text).casefold()
