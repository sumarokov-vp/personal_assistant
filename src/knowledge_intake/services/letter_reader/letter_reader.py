import encodings
from email import message_from_bytes, policy
from email.message import EmailMessage, Message

from src.knowledge_intake.models.accepted_letter import AcceptedLetter
from src.knowledge_intake.models.admitted_sender import AdmittedSender
from src.knowledge_intake.models.letter_attachment import LetterAttachment
from src.knowledge_intake.models.raw_letter import RawLetter
from src.knowledge_intake.services.letter_reader.html_text import HtmlText

MAX_BODY_CHARS = 50_000
MAX_ATTACHMENT_CHARS = 20_000
TEXT_MAINTYPE = "text"
FALLBACK_CHARSET = "utf-8"


class LetterReader:
    def __init__(self, html_text: HtmlText) -> None:
        self._html_text = html_text

    def read(self, letter: RawLetter, sender: AdmittedSender) -> AcceptedLetter:
        message = message_from_bytes(letter.content, policy=policy.default)
        return AcceptedLetter(
            uid=letter.uid,
            sender=sender,
            subject=str(message.get("Subject", "")),
            message_id=str(message.get("Message-ID", "")).strip(),
            body=self._body(message)[:MAX_BODY_CHARS],
            attachments=_attachments(message),
        )

    def _body(self, message: Message) -> str:
        if not isinstance(message, EmailMessage):
            return ""
        part = message.get_body(preferencelist=("plain", "html"))
        if part is None:
            return ""
        text = _decoded_text(part)
        if part.get_content_subtype() == "html":
            return self._html_text.convert(text)
        return text.strip()


def _attachments(message: Message) -> list[LetterAttachment]:
    if not isinstance(message, EmailMessage):
        return []
    return [
        LetterAttachment(
            filename=part.get_filename() or "без имени",
            text=_decoded_text(part)[:MAX_ATTACHMENT_CHARS]
            if part.get_content_maintype() == TEXT_MAINTYPE
            else None,
        )
        for part in message.iter_attachments()
    ]


def _decoded_text(part: Message) -> str:
    payload = part.get_payload(decode=True)
    if not isinstance(payload, bytes):
        return ""
    return payload.decode(_known_charset(part.get_content_charset()), errors="replace")


def _known_charset(charset: str | None) -> str:
    if charset and encodings.search_function(charset.lower()) is not None:
        return charset
    return FALLBACK_CHARSET
