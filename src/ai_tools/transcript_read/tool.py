import json
from typing import Any, ClassVar

from ai_framework.entities.tool_context import ToolContext
from ai_framework.protocols.base_tool import BaseTool
from pydantic import BaseModel

from src.ai_tools.transcript_read.protocols.i_storage_file_opener import (
    IStorageFileOpener,
)
from src.ai_tools.transcript_read.protocols.i_timecoded_transcript_factory import (
    ITimecodedTranscriptFactory,
)
from src.ai_tools.transcript_read.transcript_part import TranscriptPart
from src.ai_tools.transcript_read.transcript_read_error import TranscriptReadError

PART_MAX_CHARS = 40_000
MAX_TRANSCRIPT_BYTES = 64 * 1024 * 1024


class TranscriptReadInput(BaseModel):
    path: str
    part: int = 1


class TranscriptReadTool(BaseTool):
    name: ClassVar[str] = "transcript_read"
    description: ClassVar[str] = (
        "Читает расшифровку записи разговора (JSON сервиса распознавания из папки "
        "«Записи разговоров» хранилища) частями; только чтение. "
        "path — путь к JSON в хранилище, как его вернули поиск или дерево хранилища; "
        "part — номер части, с 1. Ответ: path, parts (сколько всего частей), part и "
        "text — реплики строками «[ЧЧ:ММ:СС] текст», не длиннее 40 000 знаков на часть; "
        "части стыкуются без потерь и повторов. "
        "Прежде чем писать протокол или пересказ, прочитать все части — с part=1 "
        "по part=parts: по одной части выводов о разговоре не делать. "
        "Прочитав всё, предложить протокол встречи или звонка и собрать "
        "выбранный инструментом protocol_make. "
        "Файл, где нет реплик распознавания (поля segments), и part вне 1..parts "
        "вернут ошибку."
    )

    Input: ClassVar[type[BaseModel]] = TranscriptReadInput

    def __init__(
        self,
        storage: IStorageFileOpener,
        transcript_factory: ITimecodedTranscriptFactory,
    ) -> None:
        self._storage = storage
        self._transcript_factory = transcript_factory

    def execute(self, input: TranscriptReadInput, context: ToolContext) -> str:  # noqa: A002
        result = self._recognition_result(input.path)
        parts = self._transcript_factory(result).parts(PART_MAX_CHARS)
        if not parts:
            raise TranscriptReadError(
                f"В расшифровке {input.path} нет ни одной реплики"
            )
        if not 1 <= input.part <= len(parts):
            raise TranscriptReadError(
                f"Части {input.part} нет: в расшифровке {input.path} "
                f"части с 1 по {len(parts)}"
            )
        return TranscriptPart(
            path=input.path,
            parts=len(parts),
            part=input.part,
            text=parts[input.part - 1],
        ).model_dump_json()

    def _recognition_result(self, path: str) -> dict[str, Any]:
        with self._storage.open_read(path) as file:
            raw = file.read(MAX_TRANSCRIPT_BYTES + 1)
        if len(raw) > MAX_TRANSCRIPT_BYTES:
            raise TranscriptReadError(
                f"{path} больше {MAX_TRANSCRIPT_BYTES // (1024 * 1024)} МБ — "
                "это не расшифровка"
            )
        result = _parsed_json(raw, path)
        if not isinstance(result, dict) or not isinstance(result.get("segments"), list):
            raise TranscriptReadError(
                f"{path} — не JSON распознавания: нет списка реплик segments"
            )
        return result


def _parsed_json(raw: bytes, path: str) -> object:
    try:
        return json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise TranscriptReadError(
            f"{path} — не JSON распознавания: файл не читается как JSON"
        ) from error
