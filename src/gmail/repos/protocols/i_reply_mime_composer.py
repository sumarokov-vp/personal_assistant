from collections.abc import Sequence
from typing import Protocol

from src.gmail.models.composed_mail import ComposedMail
from src.gmail.models.reply_target import ReplyTarget
from src.gmail.repos.protocols.i_outgoing_attachment import IOutgoingAttachment


class IReplyMimeComposer(Protocol):
    def reply_subject(self, subject: str) -> str: ...

    def compose_reply(
        self,
        target: ReplyTarget,
        body: str,
        attachments: Sequence[IOutgoingAttachment],
    ) -> ComposedMail: ...

    def compose_new(
        self,
        recipient: str,
        subject: str,
        body: str,
        attachments: Sequence[IOutgoingAttachment],
    ) -> ComposedMail: ...
