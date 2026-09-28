from typing import Protocol

from src.colleague_mail.models.colleague_message import ColleagueMessage


class IUnshownMailJournal(Protocol):
    def unshown_incoming(
        self, peer: str | None, message_type: str | None, limit: int | None
    ) -> list[ColleagueMessage]: ...

    def mark_shown(self, ids: list[int]) -> None: ...
