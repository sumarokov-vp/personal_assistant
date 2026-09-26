import re
from html.parser import HTMLParser

SKIPPED_TAGS = frozenset({"script", "style", "head", "title"})
BLOCK_TAGS = frozenset(
    {
        "br",
        "p",
        "div",
        "tr",
        "li",
        "ul",
        "ol",
        "table",
        "blockquote",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "hr",
    }
)


class HtmlToTextConverter:
    def convert(self, html: str) -> str:
        collector = _TextCollector()
        collector.feed(html)
        collector.close()
        return _normalize_whitespace("".join(collector.chunks))


class _TextCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.chunks: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in SKIPPED_TAGS:
            self._skip_depth += 1
        elif tag in BLOCK_TAGS:
            self.chunks.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in SKIPPED_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)
        elif tag in BLOCK_TAGS:
            self.chunks.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0:
            self.chunks.append(data)


def _normalize_whitespace(text: str) -> str:
    lines = [re.sub(r"[ \t ]+", " ", line).strip() for line in text.splitlines()]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()
