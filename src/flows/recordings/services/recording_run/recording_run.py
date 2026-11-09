import json
import mimetypes
from datetime import datetime, tzinfo
from pathlib import PurePosixPath
from typing import Any

from src.flows.recordings.services.entities.recorded_transcript import (
    RecordedTranscript,
)
from src.flows.recordings.services.entities.recording_request import RecordingRequest
from src.flows.recordings.services.recording_run.protocols.i_recognition_jobs import (
    IRecognitionJobs,
)
from src.flows.recordings.services.recording_run.protocols.i_recording_downloader import (
    IRecordingDownloader,
)
from src.flows.recordings.services.recording_run.protocols.i_recording_outcome import (
    IRecordingOutcome,
)
from src.flows.recordings.services.recording_run.protocols.i_recording_work_folder import (
    IRecordingWorkFolder,
)
from src.flows.recordings.services.recording_run.protocols.i_transcript_memory import (
    ITranscriptMemory,
)
from src.flows.recordings.services.recording_run.protocols.i_transcripts_storage import (
    ITranscriptsStorage,
)
from src.flows.recordings.services.recording_run.recognition_failure_text import (
    RecognitionFailureText,
)
from src.voice_recognition.errors import VoiceRecognitionError

DEFAULT_POLL_INTERVAL_SECONDS = 10.0
DEFAULT_MAX_WAIT_SECONDS = 2 * 60 * 60.0
WORK_FILE_SOURCE = "recording"
FALLBACK_MEDIA_TYPE = "application/octet-stream"
FALLBACK_TRANSCRIPT_STEM = "Запись"
TRANSCRIPT_SUFFIX = ".json"
TRANSCRIPT_SOURCE = "transcript"
TRANSCRIPT_MEDIA_TYPE = "application/json"
RUSSIAN_DATE_FORMAT = "%d.%m.%Y"


class RecordingRun:
    def __init__(
        self,
        downloader: IRecordingDownloader,
        work_folder: IRecordingWorkFolder,
        recognition: IRecognitionJobs,
        transcripts: ITranscriptsStorage,
        outcome: IRecordingOutcome,
        failure_text: RecognitionFailureText,
        transcripts_folder: str,
        memory: ITranscriptMemory,
        timezone: tzinfo,
        poll_interval: float = DEFAULT_POLL_INTERVAL_SECONDS,
        max_wait: float = DEFAULT_MAX_WAIT_SECONDS,
    ) -> None:
        self._downloader = downloader
        self._work_folder = work_folder
        self._recognition = recognition
        self._transcripts = transcripts
        self._outcome = outcome
        self._failure_text = failure_text
        self._transcripts_folder = transcripts_folder
        self._memory = memory
        self._timezone = timezone
        self._poll_interval = poll_interval
        self._max_wait = max_wait

    def run(self, request: RecordingRequest) -> None:
        content = self._downloader.download_document(request.file_id)
        media_type = mimetypes.guess_type(request.file_name)[0] or FALLBACK_MEDIA_TYPE
        work_file = self._work_folder.put(
            content, request.file_name, media_type, WORK_FILE_SOURCE
        )
        try:
            transcript = self._recognize(work_file.id, request.file_name)
        except VoiceRecognitionError as error:
            self._outcome.failed(
                request.chat_id, request.file_name, self._failure_text.reason(error)
            )
            return
        finally:
            self._work_folder.remove(work_file.id)
        self._memory.remember(transcript)
        self._outcome.ready(request.chat_id, transcript)

    def _recognize(self, work_file_id: str, file_name: str) -> RecordedTranscript:
        job_id = self._recognition.submit(self._work_folder.path(work_file_id))
        result = self._recognition.wait_for_result(
            job_id, poll_interval=self._poll_interval, max_wait=self._max_wait
        )
        return self._keep(file_name, result)

    def _keep(self, file_name: str, result: dict[str, Any]) -> RecordedTranscript:
        content = json.dumps(result, ensure_ascii=False, indent=2).encode()
        transcript_path = self._transcripts.write_new_file(
            self._transcripts_folder, _transcript_name(file_name), content
        )
        work_copy = self._work_folder.put(
            content,
            PurePosixPath(transcript_path).name,
            TRANSCRIPT_MEDIA_TYPE,
            TRANSCRIPT_SOURCE,
        )
        return RecordedTranscript(
            transcript_id=work_copy.id,
            recording_name=file_name,
            transcript_path=transcript_path,
            recorded_on=datetime.now(self._timezone).strftime(RUSSIAN_DATE_FORMAT),
            result=result,
        )


def _transcript_name(file_name: str) -> str:
    stem = PurePosixPath(file_name.replace("\\", "/")).stem.strip().lstrip(".").strip()
    return f"{stem or FALLBACK_TRANSCRIPT_STEM}{TRANSCRIPT_SUFFIX}"
