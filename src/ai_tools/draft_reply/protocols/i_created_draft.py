from typing import Protocol


class ICreatedDraft(Protocol):
    @property
    def id(self) -> str: ...

    @property
    def thread_id(self) -> str: ...

    @property
    def recipient(self) -> str: ...

    @property
    def subject(self) -> str: ...

    @property
    def url(self) -> str: ...
