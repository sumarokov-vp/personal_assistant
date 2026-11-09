from logging import getLogger
from threading import Thread

from src.flows.recordings.services.background_protocol.protocols.i_protocol_crash_report import (
    IProtocolCrashReport,
)
from src.flows.recordings.services.background_protocol.protocols.i_protocol_run import (
    IProtocolRun,
)
from src.flows.recordings.services.entities.protocol_request import ProtocolRequest

PROTOCOL_THREAD_PREFIX = "protocol-"
CRASH_TEXT = "Протокол не составлен: внутренняя ошибка бота, подробности — в логе."

logger = getLogger(__name__)


class BackgroundProtocolMaker:
    def __init__(
        self, protocol_run: IProtocolRun, crash_report: IProtocolCrashReport
    ) -> None:
        self._protocol_run = protocol_run
        self._crash_report = crash_report

    def start(self, request: ProtocolRequest) -> None:
        Thread(
            target=self._run_in_background,
            args=(request,),
            name=f"{PROTOCOL_THREAD_PREFIX}{request.kind.value}-{request.transcript_id}",
            daemon=True,
        ).start()

    def _run_in_background(self, request: ProtocolRequest) -> None:
        logger.info(
            "Protocol %s %s: started", request.kind.value, request.transcript_id
        )
        try:
            self._protocol_run.run(request)
        except Exception:
            logger.exception("Protocol %s: run crashed", request.transcript_id)
            self._crash_report.send_html(request.chat_id, CRASH_TEXT)
            return
        logger.info(
            "Protocol %s %s: finished", request.kind.value, request.transcript_id
        )
