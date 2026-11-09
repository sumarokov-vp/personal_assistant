from pathlib import Path

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
from src.protocols.services.typst_protocol_source.typst_markup import (
    bullet_list,
    escaped,
    heading,
    numbered_list,
    table,
)

TEMPLATE_PATH = Path(__file__).with_name("protocol.typ")
ACTIONS_HEADER = ["№", "Что", "Кто", "Срок"]
NO_DUE = "—"


class TypstProtocolSource:
    def __init__(self, template_path: Path = TEMPLATE_PATH) -> None:
        self._template = template_path.read_text(encoding="utf-8")

    def document_title(self, content: ProtocolContent) -> str:
        return DOCUMENT_TITLES[content.kind]

    def render(self, content: ProtocolContent) -> str:
        sections = [
            self._parties(content),
            self._section(AGENDA_TITLE, numbered_list(content.agenda)),
            self._discussion(content),
            self._section(
                AGREEMENTS_TITLES[content.kind], numbered_list(content.agreements)
            ),
            self._actions(content),
            self._section(OPEN_QUESTIONS_TITLE, bullet_list(content.open_questions)),
        ]
        return (
            self._template.replace("{{document_title}}", self.document_title(content))
            .replace("{{subtitle}}", escaped(content.title))
            .replace("{{date}}", content.date)
            .replace(
                "{{body}}", "\n\n".join(section for section in sections if section)
            )
        )

    def _parties(self, content: ProtocolContent) -> str:
        lines = [
            f"- *{escaped(party)}:* {escaped(', '.join(members))}"
            for party, members in content.parties.items()
        ]
        return self._section(PARTIES_TITLES[content.kind], "\n".join(lines))

    def _discussion(self, content: ProtocolContent) -> str:
        topics = [
            f"{heading(escaped(topic.topic), level=2)}\n\n{bullet_list(topic.points)}"
            for topic in content.discussion
        ]
        return self._section(DISCUSSION_TITLE, "\n\n".join(topics))

    def _actions(self, content: ProtocolContent) -> str:
        rows = [
            [str(number), action.what, action.who, action.due or NO_DUE]
            for number, action in enumerate(content.actions, start=1)
        ]
        return self._section(ACTIONS_TITLE, table(ACTIONS_HEADER, rows) if rows else "")

    @staticmethod
    def _section(title: str, body: str) -> str:
        return f"{heading(title)}\n\n{body}" if body else ""
