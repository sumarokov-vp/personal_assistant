from dataclasses import dataclass
from pathlib import PurePosixPath

from src.wiki.models.wiki_page import WikiPage
from src.wiki.search.protocols.i_wiki_page_source import IWikiPageSource
from src.wiki.search.wiki_search_hit import WikiSearchHit

EXCLUDED_DIRECTORIES = frozenset({".obsidian", "files", "Excalidraw"})
SNIPPET_LINES = 2
SNIPPET_LINE_LIMIT = 200
FRONTMATTER_FENCE = "---"


@dataclass(frozen=True)
class _RankedHit:
    name_matches: int
    phrase_in_name: bool
    phrase_in_text: bool
    occurrences: int
    hit: WikiSearchHit

    def sort_key(self) -> tuple[int, int, int, int, str]:
        return (
            -int(self.phrase_in_name),
            -self.name_matches,
            -int(self.phrase_in_text),
            -self.occurrences,
            self.hit.path,
        )


class WikiSearcher:
    def __init__(
        self,
        pages: IWikiPageSource,
        excluded_directories: frozenset[str] = EXCLUDED_DIRECTORIES,
    ) -> None:
        self._pages = pages
        self._excluded_directories = excluded_directories

    def search(self, query: str, limit: int) -> list[WikiSearchHit]:
        phrase = " ".join(query.lower().split())
        if not phrase or limit < 1:
            return []
        terms = phrase.split()
        ranked = [
            ranked_hit
            for page in self._pages.read_all_pages()
            if not self._is_excluded(page.path)
            and (ranked_hit := _rank(page, phrase, terms)) is not None
        ]
        ranked.sort(key=_RankedHit.sort_key)
        return [ranked_hit.hit for ranked_hit in ranked[:limit]]

    def _is_excluded(self, path: str) -> bool:
        directories = PurePosixPath(path).parts[:-1]
        return bool(self._excluded_directories.intersection(directories))


def _rank(page: WikiPage, phrase: str, terms: list[str]) -> _RankedHit | None:
    name = PurePosixPath(page.path).stem.lower()
    text = page.content.lower()
    if not all(term in name or term in text for term in terms):
        return None
    return _RankedHit(
        name_matches=sum(term in name for term in terms),
        phrase_in_name=phrase in name,
        phrase_in_text=phrase in text,
        occurrences=sum(text.count(term) for term in terms),
        hit=WikiSearchHit(
            path=page.path,
            title=_title(page),
            snippet=_snippet(page.content, phrase, terms),
        ),
    )


def _body_lines(content: str) -> list[str]:
    lines = content.splitlines()
    if lines and lines[0].strip() == FRONTMATTER_FENCE:
        closing = next(
            (
                index
                for index, line in enumerate(lines[1:], start=1)
                if line.strip() == FRONTMATTER_FENCE
            ),
            None,
        )
        if closing is not None:
            return lines[closing + 1 :]
    return lines


def _title(page: WikiPage) -> str:
    heading = next(
        (line for line in _body_lines(page.content) if line.startswith("# ")),
        None,
    )
    if heading is not None:
        return heading[2:].strip()
    return PurePosixPath(page.path).stem


def _snippet(content: str, phrase: str, terms: list[str]) -> str:
    lines = [line.strip() for line in _body_lines(content)]
    non_empty = [line for line in lines if line]
    start = next(
        (index for index, line in enumerate(non_empty) if phrase in line.lower()),
        None,
    )
    if start is None:
        start = next(
            (
                index
                for index, line in enumerate(non_empty)
                if any(term in line.lower() for term in terms)
            ),
            0,
        )
    window = non_empty[start : start + SNIPPET_LINES]
    return "\n".join(_clip(line) for line in window)


def _clip(line: str) -> str:
    if len(line) <= SNIPPET_LINE_LIMIT:
        return line
    return line[: SNIPPET_LINE_LIMIT - 1] + "…"
