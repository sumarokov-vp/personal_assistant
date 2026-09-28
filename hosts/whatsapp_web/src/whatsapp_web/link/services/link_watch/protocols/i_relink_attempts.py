from typing import Protocol

from whatsapp_web.link.models.relink_start import RelinkStart


class IRelinkAttempts(Protocol):
    def attempt_running(self) -> bool: ...

    def request_attempt(self, force: bool) -> RelinkStart: ...
