from collections.abc import Sequence
from email.message import EmailMessage

from src.gmail.models.composed_mail import ComposedMail
from src.gmail.models.reply_target import ReplyTarget
from src.gmail.services.reply_mime_composer.protocols.i_outgoing_attachment import (
    IOutgoingAttachment,
)

REPLY_PREFIX = "Re:"
GMAIL_MESSAGE_LIMIT_BYTES = 25 * 1024 * 1024
FALLBACK_MEDIA_TYPE = ("application", "octet-stream")


class ReplyMimeComposer:
    def __init__(self, message_limit_bytes: int = GMAIL_MESSAGE_LIMIT_BYTES) -> None:
        self._message_limit_bytes = message_limit_bytes

    def reply_subject(self, subject: str) -> str:
        if subject.lower().startswith(REPLY_PREFIX.lower()):
            return subject
        return f"{REPLY_PREFIX} {subject}".strip()

    def compose_reply(
        self,
        target: ReplyTarget,
        body: str,
        attachments: Sequence[IOutgoingAttachment],
    ) -> ComposedMail:
        headers = {
            "To": target.recipient,
            "Subject": self.reply_subject(target.subject),
        }
        if target.message_id_header:
            headers["In-Reply-To"] = target.message_id_header
            headers["References"] = " ".join(
                part for part in (target.references, target.message_id_header) if part
            )
        return self._compose_within_limit(headers, body, attachments)

    def compose_new(
        self,
        recipient: str,
        subject: str,
        body: str,
        attachments: Sequence[IOutgoingAttachment],
    ) -> ComposedMail:
        return self._compose_within_limit(
            {"To": recipient, "Subject": subject}, body, attachments
        )

    def _compose_within_limit(
        self,
        headers: dict[str, str],
        body: str,
        attachments: Sequence[IOutgoingAttachment],
    ) -> ComposedMail:
        attached: list[IOutgoingAttachment] = []
        left_out: list[str] = []
        content = _build(headers, body, attached)
        for attachment in attachments:
            if len(content) + _base64_size(len(attachment.content)) > (
                self._message_limit_bytes
            ):
                left_out.append(attachment.key)
                continue
            candidate = _build(headers, body, [*attached, attachment])
            if len(candidate) > self._message_limit_bytes:
                left_out.append(attachment.key)
                continue
            attached.append(attachment)
            content = candidate
        return ComposedMail(
            content=content,
            attached=[attachment.key for attachment in attached],
            left_out=left_out,
        )


def _build(
    headers: dict[str, str], body: str, attachments: Sequence[IOutgoingAttachment]
) -> bytes:
    message = EmailMessage()
    for name, value in headers.items():
        message[name] = value
    message.set_content(body)
    for attachment in attachments:
        maintype, subtype = _split_media_type(attachment.media_type)
        message.add_attachment(
            attachment.content,
            maintype=maintype,
            subtype=subtype,
            filename=attachment.name,
        )
    return message.as_bytes()


def _split_media_type(media_type: str) -> tuple[str, str]:
    maintype, _, subtype = media_type.partition("/")
    if not maintype or not subtype:
        return FALLBACK_MEDIA_TYPE
    return maintype, subtype


def _base64_size(raw_size: int) -> int:
    return (raw_size + 2) // 3 * 4
