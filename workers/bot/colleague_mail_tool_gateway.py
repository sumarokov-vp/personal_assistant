from src.colleague_mail.models import ColleagueMessageType
from src.colleague_mail.services.entities import OutgoingMail
from src.colleague_mail.services.sender import ColleagueMailSender, SendResult


class ColleagueMailToolGateway:
    def __init__(self, sender: ColleagueMailSender) -> None:
        self._sender = sender

    def send(
        self,
        recipient: str,
        message_type: str,
        text: str,
        in_reply_to: str | None,
        about_agent: str | None,
    ) -> SendResult:
        return self._sender.send(
            OutgoingMail(
                recipient=recipient,
                type=ColleagueMessageType(message_type),
                text=text,
                in_reply_to=in_reply_to,
                about_agent=about_agent,
            )
        )
