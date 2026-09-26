from typing import Protocol


class IFoundMail(Protocol):
    @property
    def id(self) -> str: ...

    @property
    def thread_id(self) -> str: ...

    @property
    def sender(self) -> str: ...

    @property
    def subject(self) -> str: ...

    @property
    def date(self) -> str: ...

    @property
    def snippet(self) -> str: ...
