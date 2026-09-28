from typing import Protocol

from src.colleague_mail.services.entities.incoming_mail import IncomingMail
from src.colleague_mail.services.entities.receive_outcome import ReceiveOutcome


class IIncomingMailReceiver(Protocol):
    def receive(self, incoming: IncomingMail) -> ReceiveOutcome: ...
