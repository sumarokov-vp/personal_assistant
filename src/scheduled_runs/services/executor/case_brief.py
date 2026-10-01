from dataclasses import dataclass


@dataclass(frozen=True)
class CaseBrief:
    title: str | None
    text: str
