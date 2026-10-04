from dataclasses import dataclass


@dataclass(frozen=True)
class LetterAttachment:
    filename: str
    text: str | None
