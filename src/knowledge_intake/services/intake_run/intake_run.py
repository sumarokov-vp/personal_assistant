from src.knowledge_intake.models.accepted_letter import AcceptedLetter
from src.knowledge_intake.models.admitted_sender import AdmittedSender
from src.knowledge_intake.models.knowledge_entry import KnowledgeEntry
from src.knowledge_intake.models.mailbox_folder import MailboxFolder
from src.knowledge_intake.models.raw_letter import RawLetter
from src.knowledge_intake.services.entities.intake_report import (
    DeclinedLetter,
    IntakeReport,
    MergedLetter,
    RejectedLetter,
)
from src.knowledge_intake.services.intake_run.protocols.i_distiller import IDistiller
from src.knowledge_intake.services.intake_run.protocols.i_letter_reader import (
    ILetterReader,
)
from src.knowledge_intake.services.intake_run.protocols.i_mailbox import IMailbox
from src.knowledge_intake.services.intake_run.protocols.i_publisher import IPublisher
from src.knowledge_intake.services.intake_run.protocols.i_sender_gate import (
    ISenderGate,
)

NO_REASON = "без причины"


class IntakeRun:
    def __init__(
        self,
        mailbox: IMailbox,
        gate: ISenderGate,
        reader: ILetterReader,
        distiller: IDistiller,
        publisher: IPublisher,
    ) -> None:
        self._mailbox = mailbox
        self._gate = gate
        self._reader = reader
        self._distiller = distiller
        self._publisher = publisher

    def execute(self) -> IntakeReport:
        report = IntakeReport()
        admitted = self._admitted(self._mailbox.unread(), report)
        if not admitted:
            return report
        self._publisher.prepare()
        published: list[tuple[AcceptedLetter, KnowledgeEntry]] = []
        for raw, sender in admitted:
            letter = self._reader.read(raw, sender)
            outcome = self._distiller.distill(letter)
            if outcome.entry is None:
                self._mailbox.move(raw.uid, MailboxFolder.PROCESSED)
                report.declined.append(
                    DeclinedLetter(
                        sender=sender.signature(),
                        subject=letter.subject,
                        reason=outcome.refusal or NO_REASON,
                    )
                )
                continue
            self._publisher.publish(outcome.entry, letter)
            published.append((letter, outcome.entry))
        self._close_publication(published, report)
        return report

    def _admitted(
        self, letters: list[RawLetter], report: IntakeReport
    ) -> list[tuple[RawLetter, AdmittedSender]]:
        admitted: list[tuple[RawLetter, AdmittedSender]] = []
        for raw in letters:
            verdict = self._gate.admit(raw)
            if verdict.sender is None:
                self._mailbox.move(raw.uid, MailboxFolder.REJECTED)
                report.rejected.append(
                    RejectedLetter(
                        address=verdict.address, reason=verdict.reason or NO_REASON
                    )
                )
                continue
            admitted.append((raw, verdict.sender))
        return admitted

    def _close_publication(
        self,
        published: list[tuple[AcceptedLetter, KnowledgeEntry]],
        report: IntakeReport,
    ) -> None:
        outcome = self._publisher.finish()
        if not outcome.pushed:
            report.publish_error = outcome.error or NO_REASON
            report.unpublished = len(published)
            return
        report.versions = outcome.versions
        for (letter, entry), sha in zip(published, outcome.commit_shas, strict=True):
            self._mailbox.move(letter.uid, MailboxFolder.PROCESSED)
            report.merged.append(
                MergedLetter(
                    plugin=entry.plugin,
                    topic=entry.topic,
                    sender=letter.sender.signature(),
                    commit_sha=sha,
                )
            )
