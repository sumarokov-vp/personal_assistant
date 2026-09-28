from typing import Protocol


class ISendResult(Protocol):
    @property
    def message_id(self) -> str: ...

    @property
    def outcome(self) -> str: ...
