import base64
from email.message import EmailMessage

from src.gmail.models.reply_target import ReplyTarget

REPLY_PREFIX = "Re:"


class ReplyMimeComposer:
    def reply_subject(self, subject: str) -> str:
        if subject.lower().startswith(REPLY_PREFIX.lower()):
            return subject
        return f"{REPLY_PREFIX} {subject}".strip()

    def compose_raw(self, target: ReplyTarget, body: str) -> str:
        message = EmailMessage()
        message["To"] = target.recipient
        message["Subject"] = self.reply_subject(target.subject)
        if target.message_id_header:
            message["In-Reply-To"] = target.message_id_header
            message["References"] = " ".join(
                part for part in (target.references, target.message_id_header) if part
            )
        message.set_content(body)
        return base64.urlsafe_b64encode(message.as_bytes()).decode()
