from collections.abc import Callable
from datetime import date

from src.checkup.models.checkup_journal_entry import CheckupJournalEntry
from src.checkup.models.checkup_key import CheckupKey
from src.checkup.services.checkup_actions.checkup_action_outcome import (
    CheckupActionOutcome,
)
from src.checkup.services.checkup_actions.checkup_action_result import (
    CheckupActionResult,
)
from src.checkup.services.checkup_actions.checkup_key_error import CheckupKeyError
from src.checkup.services.checkup_actions.protocols.i_assistant_task_creator import (
    IAssistantTaskCreator,
)
from src.checkup.services.checkup_actions.protocols.i_checkup_journal import (
    ICheckupJournal,
)
from src.checkup.services.entities.checkup_run import CheckupRun
from src.checkup.services.entities.created_checkup_task import CreatedCheckupTask

SKIPPED_DONE = "пропущено: у владельца уже есть задача"


class CheckupActionService:
    def __init__(
        self,
        journal: ICheckupJournal,
        task_creator: IAssistantTaskCreator,
        today: Callable[[], date],
    ) -> None:
        self._journal = journal
        self._task_creator = task_creator
        self._today = today

    def create_task(
        self, raw_key: str, content: str, due: str, reason: str, run: CheckupRun
    ) -> CheckupActionResult:
        key = self._parse_key(raw_key)
        existing = self._journal.find(key.text)
        if existing is not None:
            return CheckupActionResult(
                outcome=CheckupActionOutcome.ALREADY_DONE, journal_entry=existing
            )
        card = self._task_creator.create_assistant_task(
            content=content, due=due, description=reason
        )
        entry = CheckupJournalEntry(
            key=key.text,
            when=self._today(),
            done=f"создана задача «{card.content}»",
            task=card.url,
            reason=reason,
        )
        self._journal.record(entry)
        run.add_created(
            CreatedCheckupTask(
                key=key.text,
                content=card.content,
                due=card.due.date if card.due is not None else due,
                reason=reason,
                url=card.url,
            )
        )
        return CheckupActionResult(
            outcome=CheckupActionOutcome.CREATED, journal_entry=entry
        )

    def skip(self, raw_key: str, reason: str) -> CheckupActionResult:
        key = self._parse_key(raw_key)
        existing = self._journal.find(key.text)
        if existing is not None:
            return CheckupActionResult(
                outcome=CheckupActionOutcome.ALREADY_DONE, journal_entry=existing
            )
        entry = CheckupJournalEntry(
            key=key.text, when=self._today(), done=SKIPPED_DONE, reason=reason
        )
        self._journal.record(entry)
        return CheckupActionResult(
            outcome=CheckupActionOutcome.SKIPPED, journal_entry=entry
        )

    @staticmethod
    def _parse_key(raw_key: str) -> CheckupKey:
        key = CheckupKey.parse(raw_key)
        if key is None:
            raise CheckupKeyError(raw_key)
        return key
