import json
from datetime import datetime, tzinfo
from logging import getLogger
from pathlib import Path, PurePosixPath
from typing import Any

from src.files.work_folder.work_file_not_found_error import WorkFileNotFoundError
from src.flows.recordings.services.entities.protocol_request import ProtocolRequest
from src.flows.recordings.services.entities.recorded_transcript import (
    RecordedTranscript,
)
from src.flows.recordings.services.recording_run.recording_run import (
    RUSSIAN_DATE_FORMAT,
    TRANSCRIPT_SOURCE,
)
from src.flows.recordings.services.transcript_source.protocols.i_transcript_archive import (
    ITranscriptArchive,
)
from src.flows.recordings.services.transcript_source.protocols.i_transcript_recall import (
    ITranscriptRecall,
)
from src.flows.recordings.services.transcript_source.protocols.i_transcript_work_copies import (
    ITranscriptWorkCopies,
)
from src.flows.recordings.services.transcript_source.transcript_missing_error import (
    TranscriptMissingError,
)

MISSING_REASON = "расшифровки этой записи у бота больше нет — перешлите запись заново"

logger = getLogger(__name__)


class TranscriptSource:
    def __init__(
        self,
        memory: ITranscriptRecall,
        work_copies: ITranscriptWorkCopies,
        archive: ITranscriptArchive,
        timezone: tzinfo,
    ) -> None:
        self._memory = memory
        self._work_copies = work_copies
        self._archive = archive
        self._timezone = timezone

    def load(self, request: ProtocolRequest) -> RecordedTranscript:
        remembered = self._memory.recall(request.transcript_id)
        if remembered is not None:
            return remembered
        work_copy = self._work_copy(request.transcript_id)
        if work_copy is not None:
            logger.info("Protocol: transcript %s from work copy", request.transcript_id)
            return self._from_file(
                request.transcript_id,
                work_copy,
                request.archive_path or work_copy.name,
            )
        if request.archive_path is not None:
            archived = self._archive.resolve(request.archive_path)
            if archived.is_file():
                logger.info(
                    "Protocol: transcript %s from archive", request.archive_path
                )
                return self._from_file(
                    request.transcript_id, archived, request.archive_path
                )
        raise TranscriptMissingError(MISSING_REASON)

    def _work_copy(self, transcript_id: str) -> Path | None:
        try:
            work_file = self._work_copies.get(transcript_id)
        except WorkFileNotFoundError:
            return None
        if work_file.source != TRANSCRIPT_SOURCE:
            return None
        path = self._work_copies.path(transcript_id)
        return path if path.is_file() else None

    def _from_file(
        self, transcript_id: str, path: Path, transcript_path: str
    ) -> RecordedTranscript:
        return RecordedTranscript(
            transcript_id=transcript_id,
            recording_name=PurePosixPath(transcript_path).stem,
            transcript_path=transcript_path,
            recorded_on=datetime.fromtimestamp(
                path.stat().st_mtime, self._timezone
            ).strftime(RUSSIAN_DATE_FORMAT),
            result=_recognition_result(path),
        )


def _recognition_result(path: Path) -> dict[str, Any]:
    result = json.loads(path.read_bytes())
    if not isinstance(result, dict) or not isinstance(result.get("segments"), list):
        raise TranscriptMissingError(
            f"{path.name} — не расшифровка: в файле нет реплик распознавания"
        )
    return result
