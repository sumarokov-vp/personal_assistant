from dataclasses import dataclass


@dataclass(frozen=True)
class RowRejection:
    reason: str
