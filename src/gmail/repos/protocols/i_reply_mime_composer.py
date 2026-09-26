from typing import Protocol

from src.gmail.models.reply_target import ReplyTarget


class IReplyMimeComposer(Protocol):
    def reply_subject(self, subject: str) -> str: ...

    def compose_raw(self, target: ReplyTarget, body: str) -> str: ...
