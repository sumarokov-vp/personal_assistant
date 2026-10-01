from dataclasses import dataclass


@dataclass(frozen=True)
class ModelReply:
    text: str | None
    error: str | None = None
