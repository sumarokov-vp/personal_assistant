from dataclasses import dataclass


@dataclass(frozen=True)
class ParsedAgentMarkdown:
    fields: dict[str, str]
    body: str
