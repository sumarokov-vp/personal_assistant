from dataclasses import dataclass


@dataclass(frozen=True)
class RawLetter:
    uid: str
    content: bytes
