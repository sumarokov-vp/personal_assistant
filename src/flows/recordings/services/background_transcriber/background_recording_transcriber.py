from logging import getLogger
from threading import Thread

from src.flows.recordings.services.background_transcriber.protocols.i_recording_failure_report import (
    IRecordingFailureReport,
)
from src.flows.recordings.services.background_transcriber.protocols.i_recording_run import (
    IRecordingRun,
)
from src.flows.recordings.services.entities.recording_request import RecordingRequest

THREAD_NAME_PREFIX = "recording-"
CRASH_REASON = "внутренняя ошибка бота, подробности — в логе"

logger = getLogger(__name__)


class BackgroundRecordingTranscriber:
    def __init__(
        self, recording_run: IRecordingRun, failure_report: IRecordingFailureReport
    ) -> None:
        self._recording_run = recording_run
        self._failure_report = failure_report

    def transcribe(
        self,
        *,
        file_id: str,
        file_name: str,
        size_bytes: int,
        chat_id: int,
        card_message_id: int,
    ) -> None:
        request = RecordingRequest(
            file_id=file_id, file_name=file_name, size_bytes=size_bytes, chat_id=chat_id
        )
        Thread(
            target=self._run_in_background,
            args=(request,),
            name=f"{THREAD_NAME_PREFIX}{card_message_id}",
            daemon=True,
        ).start()

    def _run_in_background(self, request: RecordingRequest) -> None:
        logger.info("Recording %s: recognition started", request.file_name)
        try:
            self._recording_run.run(request)
        except Exception:
            logger.exception("Recording %s: run crashed", request.file_name)
            self._failure_report.failed(
                request.chat_id, request.file_name, CRASH_REASON
            )
            return
        logger.info("Recording %s: run finished", request.file_name)
