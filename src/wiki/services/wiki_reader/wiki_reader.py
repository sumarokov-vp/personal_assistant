import logging
from contextlib import AbstractContextManager
from pathlib import Path

from src.wiki.errors.wiki_page_not_found_error import WikiPageNotFoundError
from src.wiki.models.wiki_page import WikiPage
from src.wiki.services.wiki_reader.protocols.i_read_path_policy import IReadPathPolicy
from src.wiki.services.wiki_reader.protocols.i_wiki_refresher import IWikiRefresher

logger = logging.getLogger(__name__)


class WikiReader:
    def __init__(
        self,
        wiki_dir: Path,
        lock: AbstractContextManager[object],
        refresher: IWikiRefresher,
        path_policy: IReadPathPolicy,
    ) -> None:
        self._wiki_dir = wiki_dir
        self._lock = lock
        self._refresher = refresher
        self._path_policy = path_policy

    def read_page(self, relative_path: str) -> WikiPage:
        with self._lock:
            self._refresher.refresh()
            file = self._path_policy.resolve_for_read(relative_path)
            if not file.is_file():
                raise WikiPageNotFoundError(relative_path)
            return self._load(file)

    def read_all_pages(self) -> list[WikiPage]:
        with self._lock:
            self._refresher.refresh()
            files = sorted(
                path
                for path in self._wiki_dir.rglob("*.md")
                if path.is_file() and self._path_policy.is_readable_page(path)
            )
            return [self._load(file) for file in files]

    def _load(self, file: Path) -> WikiPage:
        return WikiPage(
            path=self._path_policy.relative_name(file),
            content=self._decode(file),
        )

    def _decode(self, file: Path) -> str:
        raw = file.read_bytes()
        content = raw.decode("utf-8", errors="replace")
        if content.encode("utf-8") != raw:
            logger.warning(
                "Страница вики не в UTF-8, нечитаемые байты заменены: %s",
                self._path_policy.relative_name(file),
            )
        return content
