from datetime import UTC, datetime
from logging import getLogger
from time import monotonic

from src.knowledge_intake import IKnowledgeModel
from src.knowledge_intake.services.intake_run.protocols.i_mailbox import IMailbox
from workers.knowledge_intake.intake_run_line import IntakeRunLine
from workers.knowledge_intake.protocols.i_intake_run_factory import IIntakeRunFactory
from workers.knowledge_intake.protocols.i_intake_summary import IIntakeSummary
from workers.knowledge_intake.protocols.i_owner_notifier import IOwnerNotifier

logger = getLogger(__name__)


class KnowledgeIntakeJob:
    def __init__(
        self,
        runs: IIntakeRunFactory,
        summary: IIntakeSummary,
        run_line: IntakeRunLine,
        notifier: IOwnerNotifier,
    ) -> None:
        self._runs = runs
        self._summary = summary
        self._run_line = run_line
        self._notifier = notifier

    def execute(self, mailbox: IMailbox, model: IKnowledgeModel) -> str | None:
        started_at = datetime.now(tz=UTC)
        started = monotonic()
        report = self._runs.create_run(mailbox, model).execute()
        logger.info(self._run_line.render(started_at, monotonic() - started, report))
        text = self._summary.render(report)
        if text is not None:
            self._notifier.notify(text)
        return text
