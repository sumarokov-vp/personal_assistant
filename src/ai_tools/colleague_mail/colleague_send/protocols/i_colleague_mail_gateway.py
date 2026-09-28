from typing import Protocol

from src.ai_tools.colleague_mail.colleague_send.protocols.i_send_result import (
    ISendResult,
)


class IColleagueMailGateway(Protocol):
    def send(
        self,
        recipient: str,
        message_type: str,
        text: str,
        in_reply_to: str | None,
        about_agent: str | None,
    ) -> ISendResult: ...
