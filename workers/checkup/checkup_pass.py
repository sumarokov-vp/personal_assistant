from logging import getLogger

from src.checkup.services.entities import CheckupRun
from workers.checkup.checkup_report import CheckupReport
from workers.checkup.protocols.i_checkup_conversation import ICheckupConversation
from workers.checkup.protocols.i_memory_fill import IMemoryFill

logger = getLogger(__name__)

KICKOFF = (
    "Проведи чекап по инструкции: сопоставь сроки из памяти с тем, где владелец будет, "
    "и действуй только инструментами checkup_create_task и checkup_skip. "
    "Закончив, ответь коротко: что сделано и что оставлено без действия."
)


class CheckupPass:
    def __init__(
        self,
        memory_fill: IMemoryFill,
        conversation: ICheckupConversation,
        thread_id: str,
    ) -> None:
        self._memory_fill = memory_fill
        self._conversation = conversation
        self._thread_id = thread_id

    def execute(self) -> CheckupReport:
        fill_summary = self._memory_fill.execute()
        logger.info("Memory fill before checkup:\n%s", fill_summary.render())
        run = CheckupRun()
        answer = self._conversation.process_message(
            self._thread_id, KICKOFF, tool_context=run.as_tool_context()
        )
        return CheckupReport(
            created=list(run.created), model_summary=answer.content or ""
        )
