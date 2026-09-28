from pydantic import BaseModel

from src.colleague_mail.services.entities.mail_send_outcome import MailSendOutcome


class SendResult(BaseModel):
    message_id: str
    outcome: MailSendOutcome
