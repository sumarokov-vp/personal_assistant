from email import policy
from email.headerregistry import Address
from email.parser import BytesHeaderParser

from src.knowledge_intake.models.admitted_sender import AdmittedSender
from src.knowledge_intake.models.raw_letter import RawLetter
from src.knowledge_intake.services.entities.dkim_result import DkimResult
from src.knowledge_intake.services.entities.gate_verdict import GateVerdict
from src.knowledge_intake.services.entities.raw_header_block import RawHeaderBlock
from src.knowledge_intake.services.sender_gate.protocols.i_allowlist import IAllowlist
from src.knowledge_intake.services.sender_gate.protocols.i_dkim_check import (
    IDkimCheck,
)

UNKNOWN_ADDRESS = "—"
DKIM_REFUSALS = {
    DkimResult.NO_SIGNATURE: "нет подписи DKIM",
    DkimResult.OTHER_DOMAIN: "подпись DKIM другого домена",
    DkimResult.INVALID: "подпись DKIM не прошла проверку",
}


class SenderGate:
    def __init__(self, allowlist: IAllowlist, dkim: IDkimCheck) -> None:
        self._allowlist = allowlist
        self._dkim = dkim

    def admit(self, letter: RawLetter) -> GateVerdict:
        block = RawHeaderBlock.parse(letter.content)
        if block is None:
            return GateVerdict(
                address=UNKNOWN_ADDRESS, reason="заголовки письма не по формату"
            )
        senders = _from_addresses(block)
        if len(senders) != 1:
            listed = (
                ", ".join(sender.addr_spec for sender in senders) or UNKNOWN_ADDRESS
            )
            return GateVerdict(address=listed, reason="в From не ровно один адрес")
        sender = senders[0]
        email = sender.addr_spec.strip().lower()
        domain = sender.domain.strip().lower()
        if not sender.username or not domain:
            return GateVerdict(
                address=email or UNKNOWN_ADDRESS, reason="адрес From без домена"
            )
        if not self._allowlist.contains(email):
            return GateVerdict(address=email, reason="нет в списке допуска")
        dkim_result = self._dkim.check(letter.content, domain)
        if dkim_result is not DkimResult.SIGNED:
            return GateVerdict(address=email, reason=DKIM_REFUSALS[dkim_result])
        return GateVerdict(
            address=email,
            sender=AdmittedSender(
                name=sender.display_name or sender.username, email=email
            ),
        )


def _from_addresses(block: RawHeaderBlock) -> list[Address]:
    headers = BytesHeaderParser(policy=policy.default).parsebytes(block.header_bytes())
    return [
        address
        for header in headers.get_all("From", [])
        for address in getattr(header, "addresses", ())
    ]
