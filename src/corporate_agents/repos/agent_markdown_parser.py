import re
from dataclasses import dataclass, field

from src.corporate_agents.repos.parsed_agent_markdown import ParsedAgentMarkdown

FRONTMATTER_FENCE = "---"
KEY_LINE = re.compile(r"^([A-Za-z_][\w-]*)\s*:(?:\s+(.*))?$")
BLOCK_INDICATORS = {"|", "|-", "|+", ">", ">-", ">+"}
DOUBLE_QUOTED_ESCAPE = re.compile(r"\\(u[0-9a-fA-F]{4}|.)")
SIMPLE_ESCAPES = {
    "n": "\n",
    "t": "\t",
    "r": "\r",
    "0": "\0",
    '"': '"',
    "\\": "\\",
    "/": "/",
}


@dataclass
class _RawField:
    head: str
    continuation: list[str] = field(default_factory=list)


class AgentMarkdownParser:
    def parse(self, text: str) -> ParsedAgentMarkdown | None:
        lines = text.lstrip("﻿").splitlines()
        if not lines or lines[0].rstrip() != FRONTMATTER_FENCE:
            return None
        closing = next(
            (
                index
                for index in range(1, len(lines))
                if lines[index].rstrip() == FRONTMATTER_FENCE
            ),
            None,
        )
        if closing is None:
            return None
        raw_fields = self._collect_fields(lines[1:closing])
        if raw_fields is None:
            return None
        fields: dict[str, str] = {}
        for key, raw in raw_fields.items():
            value = self._field_value(raw)
            if value is None:
                return None
            fields[key] = value
        body = "\n".join(lines[closing + 1 :]).strip()
        return ParsedAgentMarkdown(fields=fields, body=body)

    def _collect_fields(self, lines: list[str]) -> dict[str, _RawField] | None:
        fields: dict[str, _RawField] = {}
        current: _RawField | None = None
        for line in lines:
            is_continuation = line[:1] in (" ", "\t") or (
                not line.strip() and current is not None
            )
            if is_continuation:
                if current is None:
                    return None
                current.continuation.append(line)
                continue
            if not line.strip() or line.startswith("#"):
                current = None
                continue
            match = KEY_LINE.match(line)
            if match is None:
                return None
            current = _RawField(head=(match.group(2) or "").strip())
            fields[match.group(1)] = current
        return fields

    def _field_value(self, raw: _RawField) -> str | None:
        if raw.head in BLOCK_INDICATORS:
            return self._block_value(raw.head, raw.continuation)
        continued = [line.strip() for line in raw.continuation if line.strip()]
        value = " ".join([raw.head, *continued]).strip()
        if value.startswith('"'):
            if len(value) < 2 or not value.endswith('"'):
                return None
            return DOUBLE_QUOTED_ESCAPE.sub(_unescape, value[1:-1])
        if value.startswith("'"):
            if len(value) < 2 or not value.endswith("'"):
                return None
            return value[1:-1].replace("''", "'")
        return value

    def _block_value(self, indicator: str, lines: list[str]) -> str:
        content = [line for line in lines if line.strip()]
        indent = min((len(line) - len(line.lstrip()) for line in content), default=0)
        dedented = [line[indent:].rstrip() for line in lines]
        if indicator.startswith("|"):
            return "\n".join(dedented).strip()
        paragraphs: list[list[str]] = [[]]
        for line in dedented:
            if line:
                paragraphs[-1].append(line)
            elif paragraphs[-1]:
                paragraphs.append([])
        return "\n".join(" ".join(paragraph) for paragraph in paragraphs if paragraph)


def _unescape(match: re.Match[str]) -> str:
    sequence = match.group(1)
    if sequence.startswith("u") and len(sequence) == 5:
        return chr(int(sequence[1:], 16))
    return SIMPLE_ESCAPES.get(sequence, "\\" + sequence)
