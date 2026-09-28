from typing import Protocol

from whatsapp_web.link.models.relink_start import RelinkStart


class IRelinkTrigger(Protocol):
    def request_attempt(self, force: bool) -> RelinkStart: ...
