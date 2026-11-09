from html import escape

from src.protocols.models.protocol_content import ProtocolContent
from src.protocols.services.entities.protocol_sections import (
    ACTIONS_TITLE,
    AGENDA_TITLE,
    AGREEMENTS_TITLES,
    DISCUSSION_TITLE,
    DOCUMENT_TITLES,
    OPEN_QUESTIONS_TITLE,
    PARTIES_TITLES,
)

TELEGRAM_MESSAGE_MAX_CHARS = 4096
BLOCK_SEPARATOR = "\n\n"
LINE_SEPARATOR = "\n"
BULLET = "•"
ELLIPSIS = "…"
CONTINUED = " (продолжение)"


class TelegramProtocolText:
    def __init__(self, max_chars: int = TELEGRAM_MESSAGE_MAX_CHARS) -> None:
        self._max_chars = max_chars

    def messages(self, content: ProtocolContent) -> list[str]:
        blocks = [self._header(content), *self._sections(content)]
        return self._packed(blocks)

    def _header(self, content: ProtocolContent) -> list[str]:
        return [
            f"<b>{DOCUMENT_TITLES[content.kind]}</b>",
            f"<i>{escape(content.title)}</i>",
            escape(content.date),
        ]

    def _sections(self, content: ProtocolContent) -> list[list[str]]:
        sections = [
            self._section(
                PARTIES_TITLES[content.kind],
                [
                    f"{BULLET} <b>{escape(party)}:</b> {escape(', '.join(members))}"
                    for party, members in content.parties.items()
                ],
            ),
            self._section(AGENDA_TITLE, _numbered(content.agenda)),
            self._section(DISCUSSION_TITLE, self._discussion(content)),
            self._section(
                AGREEMENTS_TITLES[content.kind], _numbered(content.agreements)
            ),
            self._section(ACTIONS_TITLE, self._actions(content)),
            self._section(OPEN_QUESTIONS_TITLE, _bulleted(content.open_questions)),
        ]
        return [section for section in sections if section]

    def _discussion(self, content: ProtocolContent) -> list[str]:
        lines: list[str] = []
        for topic in content.discussion:
            lines.append(f"<i>{escape(topic.topic)}</i>")
            lines.extend(_bulleted(topic.points))
        return lines

    def _actions(self, content: ProtocolContent) -> list[str]:
        return [
            f"{number}. {escape(action.what)} — <b>{escape(action.who)}</b>"
            + (f", срок: {escape(action.due)}" if action.due else "")
            for number, action in enumerate(content.actions, start=1)
        ]

    @staticmethod
    def _section(title: str, lines: list[str]) -> list[str]:
        return [f"<b>{title}</b>", *lines] if lines else []

    def _packed(self, blocks: list[list[str]]) -> list[str]:
        messages: list[str] = []
        current = ""
        for block in blocks:
            for piece in self._fitting_pieces(block):
                candidate = f"{current}{BLOCK_SEPARATOR}{piece}" if current else piece
                if len(candidate) <= self._max_chars:
                    current = candidate
                    continue
                messages.append(current)
                current = piece
        if current:
            messages.append(current)
        return messages

    def _fitting_pieces(self, block: list[str]) -> list[str]:
        whole = LINE_SEPARATOR.join(block)
        if len(whole) <= self._max_chars:
            return [whole]
        title, *lines = block
        pieces: list[str] = []
        current = title
        for line in lines:
            line = self._fitting_line(line)
            candidate = f"{current}{LINE_SEPARATOR}{line}"
            if len(candidate) <= self._max_chars:
                current = candidate
                continue
            pieces.append(current)
            current = (
                f"{title.removesuffix('</b>')}{CONTINUED}</b>{LINE_SEPARATOR}{line}"
            )
        pieces.append(current)
        return pieces

    def _fitting_line(self, line: str) -> str:
        reserve = self._max_chars // 4
        if len(line) <= self._max_chars - reserve:
            return line
        return line[: self._max_chars - reserve].rsplit(" ", 1)[0] + ELLIPSIS


def _numbered(items: list[str]) -> list[str]:
    return [f"{number}. {escape(item)}" for number, item in enumerate(items, start=1)]


def _bulleted(items: list[str]) -> list[str]:
    return [f"{BULLET} {escape(item)}" for item in items]
