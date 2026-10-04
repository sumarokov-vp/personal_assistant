from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from src.knowledge_intake.models.accepted_letter import AcceptedLetter
from src.knowledge_intake.models.admitted_sender import AdmittedSender
from src.knowledge_intake.models.knowledge_entry import KnowledgeEntry
from src.knowledge_intake.models.mailbox_folder import MailboxFolder
from src.knowledge_intake.models.raw_letter import RawLetter
from src.knowledge_intake.repos.allowlist_file import AllowlistFile
from src.knowledge_intake.services.dkim_verifier.dkim_verifier import DkimVerifier
from src.knowledge_intake.services.entities.distill_outcome import DistillOutcome
from src.knowledge_intake.services.entities.push_outcome import PushOutcome
from src.knowledge_intake.services.intake_run.intake_run import IntakeRun
from src.knowledge_intake.services.sender_gate.sender_gate import SenderGate
from tests.knowledge_intake.conftest import (
    COMPANY_DOMAIN,
    EMPLOYEE,
    FOREIGN_DOMAIN,
    FOREIGN_SENDER,
    STRANGER,
    DkimKeys,
    FakeMailbox,
    build_letter,
    sign,
)


@dataclass
class RecordingReader:
    calls: list[str] = field(default_factory=list)

    def read(self, letter: RawLetter, sender: AdmittedSender) -> AcceptedLetter:
        self.calls.append(letter.uid)
        return AcceptedLetter(
            uid=letter.uid, sender=sender, subject="", message_id="", body=""
        )


class RefusingDistiller:
    def distill(self, letter: AcceptedLetter) -> DistillOutcome:
        return DistillOutcome(refusal="не знание: тест")


class IdlePublisher:
    def prepare(self) -> None:
        return None

    def publish(self, entry: KnowledgeEntry, letter: AcceptedLetter) -> None:
        raise AssertionError("в тесте допуска вливания нет")

    def finish(self) -> PushOutcome:
        return PushOutcome(pushed=True)


@pytest.fixture
def gate(tmp_path: Path, txt_lookup: Callable[..., bytes | None]) -> SenderGate:
    allowlist = tmp_path / "allowlist.txt"
    allowlist.write_text(
        f"# сотрудники\n{EMPLOYEE.upper()}\n{FOREIGN_SENDER}\n", encoding="utf-8"
    )
    return SenderGate(allowlist=AllowlistFile(allowlist), dkim=DkimVerifier(txt_lookup))


def test_rejected_letters_go_to_rejected_without_reading_body(
    gate: SenderGate, company_keys: DkimKeys, foreign_keys: DkimKeys
) -> None:
    stranger = sign(build_letter(STRANGER), company_keys, COMPANY_DOMAIN)
    unsigned = build_letter(EMPLOYEE)
    other_domain = sign(build_letter(EMPLOYEE), foreign_keys, FOREIGN_DOMAIN)
    tampered = sign(
        build_letter(EMPLOYEE, body="original advice"), company_keys, COMPANY_DOMAIN
    ).replace(b"original advice", b"replaced advice")
    mailbox = FakeMailbox(
        [
            RawLetter("1", stranger),
            RawLetter("2", unsigned),
            RawLetter("3", other_domain),
            RawLetter("4", tampered),
        ]
    )
    reader = RecordingReader()

    report = IntakeRun(
        mailbox=mailbox,
        gate=gate,
        reader=reader,
        distiller=RefusingDistiller(),
        publisher=IdlePublisher(),
    ).execute()

    assert reader.calls == []
    assert mailbox.moves == dict.fromkeys(("1", "2", "3", "4"), MailboxFolder.REJECTED)
    assert [(item.address, item.reason) for item in report.rejected] == [
        (STRANGER, "нет в списке допуска"),
        (EMPLOYEE, "нет подписи DKIM"),
        (EMPLOYEE, "подпись DKIM другого домена"),
        (EMPLOYEE, "подпись DKIM не прошла проверку"),
    ]


def test_signed_letter_from_allowed_sender_is_admitted(
    gate: SenderGate, company_keys: DkimKeys
) -> None:
    verdict = gate.admit(
        RawLetter("1", sign(build_letter(EMPLOYEE), company_keys, COMPANY_DOMAIN))
    )

    assert verdict.sender == AdmittedSender(name="Анна Тестова", email=EMPLOYEE)


def test_signature_of_sender_domain_counts_only_for_own_domain(
    gate: SenderGate, company_keys: DkimKeys
) -> None:
    signed_as_company = sign(build_letter(FOREIGN_SENDER), company_keys, COMPANY_DOMAIN)

    verdict = gate.admit(RawLetter("1", signed_as_company))

    assert verdict.sender is None
    assert verdict.reason == "подпись DKIM другого домена"


def test_two_from_addresses_are_rejected(
    gate: SenderGate, company_keys: DkimKeys
) -> None:
    raw = build_letter(EMPLOYEE).replace(
        b"From: ", f"From: {STRANGER}\r\nFrom: ".encode(), 1
    )

    verdict = gate.admit(RawLetter("1", sign(raw, company_keys, COMPANY_DOMAIN)))

    assert verdict.sender is None
    assert verdict.reason == "в From не ровно один адрес"
