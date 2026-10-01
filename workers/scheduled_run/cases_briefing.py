from logging import getLogger
from zoneinfo import ZoneInfo

from ai_framework import ToolContext

from src.ai_tools import CaseReadTool
from src.ai_tools.case_read.tool import DEFAULT_EVENTS_LIMIT, CaseReadInput
from src.cases.errors import CasesServiceError
from src.cases.models.case_feed import CaseFeed
from src.cases.services.untrusted_frame.untrusted_case_frame import UntrustedCaseFrame
from src.scheduled_runs.services.executor.case_brief import CaseBrief
from workers.scheduled_run.protocols.i_case_feed_source import ICaseFeedSource

logger = getLogger(__name__)

NO_CASES_SERVICE = "Сервис кейсов боту не подключён — кейс не прочитан."


class CasesBriefing:
    def __init__(self, cases: ICaseFeedSource, timezone: ZoneInfo) -> None:
        self._cases = cases
        self._timezone = timezone

    def brief(self, case_id: str) -> CaseBrief:
        # Кейс не прочитался — запуск всё равно идёт: инструкция владельца важнее ленты
        try:
            feed = self._cases.read_case(case_id, DEFAULT_EVENTS_LIMIT)
        except CasesServiceError as error:
            logger.warning("Scheduled run case %s not read: %s", case_id, error)
            return CaseBrief(title=None, text=f"Кейс не прочитан: {error}")
        text = CaseReadTool(
            reader=_ReadFeed(feed), frame=UntrustedCaseFrame(), timezone=self._timezone
        ).execute(CaseReadInput(case_id=case_id), ToolContext())
        return CaseBrief(title=feed.case.title, text=text)


class NoCasesBriefing:
    def brief(self, case_id: str) -> CaseBrief:  # noqa: ARG002
        return CaseBrief(title=None, text=NO_CASES_SERVICE)


class _ReadFeed:
    def __init__(self, feed: CaseFeed) -> None:
        self._feed = feed

    def read_case(self, case_id: str, events_limit: int) -> CaseFeed:  # noqa: ARG002
        return self._feed
