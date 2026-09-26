from typing import Protocol

from ai_framework import Attachment


class IChatAttachments(Protocol):
    def in_thread(self, thread_id: str) -> list[Attachment]: ...

    def content(self, attachment: Attachment) -> bytes: ...
