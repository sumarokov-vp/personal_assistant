import json
from collections.abc import Callable
from logging import getLogger
from typing import Any

from pydantic import ValidationError

from src.flows.recordings.services.entities.recorded_transcript import (
    RecordedTranscript,
)
from src.flows.recordings.services.protocol_drafter.call_protocol_draft import (
    CallProtocolDraft,
)
from src.flows.recordings.services.protocol_drafter.meeting_protocol_draft import (
    MeetingProtocolDraft,
)
from src.flows.recordings.services.protocol_drafter.protocol_draft_error import (
    ProtocolDraftError,
)
from src.flows.recordings.services.protocol_drafter.protocol_prompts import (
    ProtocolPrompts,
)
from src.flows.recordings.services.protocol_drafter.protocols.i_protocol_model import (
    IProtocolModel,
)
from src.flows.recordings.services.protocol_drafter.protocols.i_timecoded_transcript import (
    ITimecodedTranscript,
)
from src.protocols.models.protocol_content import ProtocolContent
from src.protocols.models.protocol_kind import ProtocolKind

SINGLE_CALL_MAX_CHARS = 240_000
NOTES_PART_MAX_CHARS = 120_000
ERROR_MAX_CHARS = 1500
DRAFTS: dict[ProtocolKind, type[CallProtocolDraft]] = {
    ProtocolKind.MEETING: MeetingProtocolDraft,
    ProtocolKind.CALL: CallProtocolDraft,
}
KIND_NAMES = {
    ProtocolKind.MEETING: "протокол встречи",
    ProtocolKind.CALL: "протокол звонка",
}

logger = getLogger(__name__)


class ProtocolDrafter:
    def __init__(
        self,
        model: IProtocolModel,
        prompts: ProtocolPrompts,
        timecoded: Callable[[dict[str, Any]], ITimecodedTranscript],
        single_call_max_chars: int = SINGLE_CALL_MAX_CHARS,
        notes_part_max_chars: int = NOTES_PART_MAX_CHARS,
    ) -> None:
        self._model = model
        self._prompts = prompts
        self._timecoded = timecoded
        self._single_call_max_chars = single_call_max_chars
        self._notes_part_max_chars = notes_part_max_chars

    def draft(
        self, kind: ProtocolKind, transcript: RecordedTranscript
    ) -> ProtocolContent:
        timecoded = self._timecoded(transcript.result)
        text = timecoded.text
        if not text.strip():
            raise ProtocolDraftError("в расшифровке нет ни одной реплики")
        if len(text) <= self._single_call_max_chars:
            source = f"Расшифровка разговора, реплики «[ЧЧ:ММ:СС] текст»:\n\n{text}"
        else:
            source = self._notes(timecoded.parts(self._notes_part_max_chars))
        prompt = self._protocol_prompt(kind, transcript.recorded_on, source)
        content, error = self._validated(
            kind, self._model.ask(self._prompts.protocol, prompt)
        )
        if content is not None:
            return content
        logger.warning("Protocol: model fields rejected, retrying: %s", error)
        content, error = self._validated(
            kind,
            self._model.ask(self._prompts.protocol, _with_correction(prompt, error)),
        )
        if content is not None:
            return content
        raise ProtocolDraftError(
            f"модель дважды вернула поля протокола, которые не проходят проверку: {error}"
        )

    def _notes(self, parts: list[str]) -> str:
        logger.info("Protocol: long transcript, %d parts to notes", len(parts))
        notes = [
            self._model.ask(
                self._prompts.notes,
                f"Часть {number} из {len(parts)} расшифровки разговора, реплики "
                f"«[ЧЧ:ММ:СС] текст»:\n\n{part}",
            )
            for number, part in enumerate(parts, start=1)
        ]
        joined = "\n\n".join(
            f"Конспект части {number} из {len(notes)}:\n{note}"
            for number, note in enumerate(notes, start=1)
        )
        return (
            "Разговор длинный, поэтому вместо расшифровки — подробные конспекты её "
            f"частей по порядку:\n\n{joined}"
        )

    @staticmethod
    def _protocol_prompt(kind: ProtocolKind, recorded_on: str, source: str) -> str:
        schema = json.dumps(DRAFTS[kind].model_json_schema(), ensure_ascii=False)
        return (
            f"Составь {KIND_NAMES[kind]} (kind={kind.value}).\n"
            f"Дата записи: {recorded_on} — её ставь в date, если в разговоре не "
            "названа другая дата самой встречи.\n"
            "Ответ — один JSON-объект по этой JSON-схеме, без текста до и после:\n"
            f"{schema}\n\n"
            f"{source}"
        )

    @staticmethod
    def _validated(
        kind: ProtocolKind, answer: str
    ) -> tuple[ProtocolContent | None, str]:
        try:
            draft = DRAFTS[kind].model_validate_json(_json_object(answer))
            return ProtocolContent(kind=kind, **draft.model_dump()), ""
        except ValidationError as error:
            return None, str(error)[:ERROR_MAX_CHARS]


def _with_correction(prompt: str, error: str) -> str:
    return (
        f"{prompt}\n\nПрошлый ответ не прошёл проверку полей:\n{error}\n"
        "Верни поля заново, строго по схеме."
    )


def _json_object(answer: str) -> str:
    start = answer.find("{")
    end = answer.rfind("}")
    if start == -1 or end < start:
        return answer.strip()
    return answer[start : end + 1]
