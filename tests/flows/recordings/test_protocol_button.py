import json
import threading
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from bot_framework.core.entities.bot_callback import BotCallback

from src.dropbox.services.boundary.dropbox_access_policy import DropboxAccessPolicy
from src.dropbox.services.boundary.dropbox_boundary import DropboxBoundary
from src.dropbox.services.boundary.dropbox_folder_writer import DropboxFolderWriter
from src.files.work_folder.work_folder import WorkFolder
from src.flows.recordings import MakeProtocolHandler, OutcomeMessageTranscriptPath
from src.flows.recordings.services import (
    PROTOCOL_THREAD_PREFIX,
    BackgroundProtocolMaker,
    ProtocolCallback,
    ProtocolDrafter,
    ProtocolModelError,
    ProtocolPrompts,
    ProtocolRun,
    ProtocolRunText,
    RecordedTranscript,
    RecordingLinks,
    RecordingTranscripts,
    TranscriptSource,
)
from src.protocols.models.protocol_kind import ProtocolKind
from src.protocols.services.protocol_maker import ProtocolMaker
from src.protocols.services.telegram_protocol_text import TelegramProtocolText
from src.protocols.services.typst_protocol_source import TypstProtocolSource
from src.voice_recognition.services.timecoded_transcript import TimecodedTranscript

CHAT_ID = 100
RECORDINGS_FOLDER = "Записи разговоров"
TRANSCRIPT_NAME = "Встреча с подрядчиком.json"
TRANSCRIPT_PATH = f"{RECORDINGS_FOLDER}/{TRANSCRIPT_NAME}"
FAKE_PDF = b"%PDF-1.7 fake"
RESULT: dict[str, Any] = {
    "text": "Добрый день. Сроки поставки — до пятницы.",
    "language": "ru",
    "segments": [
        {"start": 0.0, "end": 1.5, "text": "Добрый день."},
        {"start": 1.5, "end": 4.0, "text": "Сроки поставки — до пятницы."},
    ],
}
CALL_FIELDS: dict[str, Any] = {
    "title": "Подрядчик: сроки поставки",
    "date": "09.11.2026",
    "parties": {"Smartist": ["Владелец"], "Подрядчик": ["Менеджер"]},
    "agreements": ["Поставка до пятницы"],
    "actions": [{"what": "Отгрузить партию", "who": "Подрядчик", "due": "13.11.2026"}],
    "open_questions": ["Кто принимает груз"],
}
MEETING_FIELDS: dict[str, Any] = {
    **CALL_FIELDS,
    "agenda": ["Сроки поставки"],
    "discussion": [{"topic": "Сроки поставки", "points": ["Склад готов"]}],
}


class FakeModel:
    def __init__(self, answers: list[str | Exception]) -> None:
        self._answers = answers
        self.calls: list[tuple[str, str]] = []

    def ask(self, system: str, prompt: str) -> str:
        self.calls.append((system, prompt))
        answer = self._answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer


class FakeCompiler:
    def compile_pdf(self, source: str) -> bytes:
        assert "{{body}}" not in source
        return FAKE_PDF


class Chat:
    def __init__(self) -> None:
        self.events: list[tuple[str, str]] = []
        self.pdfs: list[tuple[str, bytes, str]] = []
        self.answered: list[tuple[str, str | None]] = []
        self._next_id = 1000

    def send_html(self, chat_id: int, text: str) -> int:
        assert chat_id == CHAT_ID
        self.events.append(("text", text))
        return self._id()

    def send_pdf(self, chat_id: int, file_name: str, pdf: bytes, caption: str) -> int:
        assert chat_id == CHAT_ID
        self.events.append(("pdf", file_name))
        self.pdfs.append((file_name, pdf, caption))
        return self._id()

    def answer(
        self, callback_query_id: str, text: str | None = None, show_alert: bool = False
    ) -> None:
        self.answered.append((callback_query_id, text))

    def texts(self) -> list[str]:
        return [text for kind, text in self.events if kind == "text"]

    def _id(self) -> int:
        self._next_id += 1
        return self._next_id


class ProtocolKit:
    def __init__(
        self,
        tmp_path: Path,
        answers: list[str | Exception],
        remember: bool = True,
        keep_work_copy: bool = True,
    ) -> None:
        self.chat = Chat()
        self.model = FakeModel(answers)
        self.storage_root = tmp_path / "Dropbox"
        (self.storage_root / RECORDINGS_FOLDER).mkdir(parents=True)
        (self.storage_root / TRANSCRIPT_PATH).write_text(
            json.dumps(RESULT, ensure_ascii=False), encoding="utf-8"
        )
        self.work_folder = WorkFolder(tmp_path / "work")
        work_copy = self.work_folder.put(
            json.dumps(RESULT).encode(),
            TRANSCRIPT_NAME,
            "application/json",
            "transcript",
        )
        self.transcript_id = work_copy.id
        if not keep_work_copy:
            self.work_folder.remove(work_copy.id)
        self.memory = RecordingTranscripts()
        if remember:
            self.memory.remember(
                RecordedTranscript(
                    transcript_id=self.transcript_id,
                    recording_name="Встреча с подрядчиком.m4a",
                    transcript_path=TRANSCRIPT_PATH,
                    recorded_on="09.11.2026",
                    result=RESULT,
                )
            )
        boundary = DropboxBoundary(self.storage_root, DropboxAccessPolicy())
        protocol_run = ProtocolRun(
            transcripts=TranscriptSource(
                memory=self.memory,
                work_copies=self.work_folder,
                archive=boundary,
                timezone=ZoneInfo("Asia/Almaty"),
            ),
            drafter=ProtocolDrafter(
                model=self.model,
                prompts=ProtocolPrompts(protocol="system", notes="notes"),
                timecoded=TimecodedTranscript,
            ),
            documents=ProtocolMaker(
                source=TypstProtocolSource(),
                compiler=FakeCompiler(),
                storage=DropboxFolderWriter(
                    boundary=boundary, folder=RECORDINGS_FOLDER
                ),
            ),
            text_messages=TelegramProtocolText(),
            chat=self.chat,
            text=ProtocolRunText(),
        )
        self.handler = MakeProtocolHandler(
            self.chat,
            ProtocolCallback(),
            OutcomeMessageTranscriptPath(RecordingLinks()),
            BackgroundProtocolMaker(protocol_run, self.chat),
        )

    def press(self, kind: ProtocolKind, with_outcome_link: bool = True) -> None:
        callback = BotCallback(
            id="cb",
            user_id=1,
            data=ProtocolCallback().data(kind, self.transcript_id),
            message_id=7,
            message_chat_id=CHAT_ID,
        )
        entities = (
            [
                SimpleNamespace(
                    type="text_link",
                    url=RecordingLinks().transcript_url(TRANSCRIPT_PATH),
                )
            ]
            if with_outcome_link
            else []
        )
        callback.set_original(
            SimpleNamespace(message=SimpleNamespace(entities=entities))
        )
        self.handler.handle(callback)
        for thread in threading.enumerate():
            if thread.name.startswith(PROTOCOL_THREAD_PREFIX):
                thread.join(timeout=5)
                assert not thread.is_alive()

    def archived(self) -> list[str]:
        return sorted(
            path.name
            for path in (self.storage_root / RECORDINGS_FOLDER).iterdir()
            if path.suffix in (".typ", ".pdf")
        )


def _json(fields: dict[str, Any]) -> str:
    return json.dumps(fields, ensure_ascii=False)


class TestProtocolPressed:
    def test_meeting_protocol_goes_to_chat_as_text_and_pdf_and_to_archive(
        self, tmp_path: Path
    ) -> None:
        kit = ProtocolKit(tmp_path, [_json(MEETING_FIELDS)])
        kit.press(ProtocolKind.MEETING)

        assert kit.chat.answered == [("cb", None)]
        assert kit.chat.events[0] == ("text", "Составляю протокол встречи…")
        protocol_text = "\n".join(kit.chat.texts()[1:])
        assert "<b>Протокол встречи</b>" in protocol_text
        assert "Повестка" in protocol_text
        assert "Отгрузить партию" in protocol_text
        [(pdf_name, pdf, caption)] = kit.chat.pdfs
        assert pdf == FAKE_PDF
        assert pdf_name == "2026-11-09 Протокол встречи — Подрядчик сроки поставки.pdf"
        assert RECORDINGS_FOLDER in caption
        assert kit.archived() == [
            "2026-11-09 Протокол встречи — Подрядчик сроки поставки.pdf",
            "2026-11-09 Протокол встречи — Подрядчик сроки поставки.typ",
        ]
        assert kit.chat.events[-1][0] == "pdf"

    def test_call_protocol_has_no_agenda_and_model_sees_transcript(
        self, tmp_path: Path
    ) -> None:
        kit = ProtocolKit(tmp_path, [_json(CALL_FIELDS)])
        kit.press(ProtocolKind.CALL)

        assert kit.chat.events[0] == ("text", "Составляю протокол звонка…")
        protocol_text = "\n".join(kit.chat.texts()[1:])
        assert "<b>Протокол звонка</b>" in protocol_text
        assert "Договорённости" in protocol_text
        assert "Повестка" not in protocol_text
        [(_system, prompt)] = kit.model.calls
        assert "[00:00:01] Сроки поставки — до пятницы." in prompt
        assert "09.11.2026" in prompt
        assert '"agreements"' in prompt and '"agenda"' not in prompt
        assert [name.endswith(".typ") for name in kit.archived()] == [False, True]

    def test_model_error_is_reported_without_pdf(self, tmp_path: Path) -> None:
        kit = ProtocolKit(
            tmp_path, [ProtocolModelError("модель ответила ошибкой: overloaded")]
        )
        kit.press(ProtocolKind.CALL)

        assert kit.chat.texts() == [
            "Составляю протокол звонка…",
            "Не получилось составить протокол звонка: "
            "модель ответила ошибкой: overloaded.",
        ]
        assert kit.chat.pdfs == []
        assert kit.archived() == []

    def test_model_timeout_is_reported(self, tmp_path: Path) -> None:
        kit = ProtocolKit(tmp_path, [TimeoutError()])
        kit.press(ProtocolKind.MEETING)

        assert "модель не ответила вовремя" in kit.chat.texts()[-1]
        assert kit.chat.pdfs == []

    def test_invalid_fields_are_retried_once(self, tmp_path: Path) -> None:
        kit = ProtocolKit(
            tmp_path, ['{"title": ""}', _json({**CALL_FIELDS, "date": "2026-11-09"})]
        )
        kit.press(ProtocolKind.CALL)

        assert len(kit.model.calls) == 2
        assert "не проходят проверку" in kit.chat.texts()[-1]
        assert "Traceback" not in kit.chat.texts()[-1]
        assert kit.chat.pdfs == []

    def test_retry_with_valid_fields_gives_pdf(self, tmp_path: Path) -> None:
        kit = ProtocolKit(
            tmp_path, ["не JSON", f"Вот поля:\n```json\n{_json(CALL_FIELDS)}\n```"]
        )
        kit.press(ProtocolKind.CALL)

        assert "Прошлый ответ не прошёл проверку" in kit.model.calls[1][1]
        assert len(kit.chat.pdfs) == 1

    def test_archive_failure_still_delivers_protocol(self, tmp_path: Path) -> None:
        kit = ProtocolKit(tmp_path, [_json(CALL_FIELDS)])
        folder = kit.storage_root / RECORDINGS_FOLDER
        for path in folder.iterdir():
            path.unlink()
        folder.rmdir()
        folder.write_text("не папка")

        kit.press(ProtocolKind.CALL)

        [(_name, pdf, caption)] = kit.chat.pdfs
        assert pdf == FAKE_PDF
        assert RECORDINGS_FOLDER not in caption
        assert kit.chat.texts()[-1].startswith(
            "Копию протокола в архив записей не сохранил"
        )


class TestTranscriptSources:
    def test_work_copy_serves_when_memory_is_empty(self, tmp_path: Path) -> None:
        kit = ProtocolKit(tmp_path, [_json(CALL_FIELDS)], remember=False)
        (kit.storage_root / TRANSCRIPT_PATH).unlink()

        kit.press(ProtocolKind.CALL)

        assert len(kit.chat.pdfs) == 1

    def test_archive_serves_when_work_copy_is_gone(self, tmp_path: Path) -> None:
        kit = ProtocolKit(
            tmp_path, [_json(CALL_FIELDS)], remember=False, keep_work_copy=False
        )
        kit.press(ProtocolKind.CALL)

        assert len(kit.chat.pdfs) == 1
        assert "Сроки поставки" in kit.model.calls[0][1]

    def test_lost_transcript_asks_to_resend(self, tmp_path: Path) -> None:
        kit = ProtocolKit(
            tmp_path, [_json(CALL_FIELDS)], remember=False, keep_work_copy=False
        )
        kit.press(ProtocolKind.CALL, with_outcome_link=False)

        assert "перешлите запись заново" in kit.chat.texts()[-1]
        assert kit.model.calls == []


def test_malformed_callback_gets_alert(tmp_path: Path) -> None:
    kit = ProtocolKit(tmp_path, [])
    kit.handler.handle(
        BotCallback(
            id="cb", user_id=1, data="prt:x:zz", message_id=7, message_chat_id=CHAT_ID
        )
    )

    assert kit.chat.answered == [("cb", "Карточка устарела — перешлите запись заново.")]
    assert kit.chat.events == []


@pytest.mark.parametrize("kind", list(ProtocolKind))
def test_long_transcript_goes_through_part_notes(kind: ProtocolKind) -> None:
    segments = [
        {"start": float(second), "end": float(second + 1), "text": f"Реплика {second}."}
        for second in range(300)
    ]
    fields = MEETING_FIELDS if kind == ProtocolKind.MEETING else CALL_FIELDS
    parts = TimecodedTranscript({"segments": segments}).parts(2000)
    assert len(parts) > 1
    notes: list[str | Exception] = [f"конспект {n}" for n in range(1, len(parts) + 1)]
    model = FakeModel([*notes, _json(fields)])
    drafter = ProtocolDrafter(
        model=model,
        prompts=ProtocolPrompts(protocol="system", notes="notes"),
        timecoded=TimecodedTranscript,
        single_call_max_chars=3000,
        notes_part_max_chars=2000,
    )
    transcript = RecordedTranscript(
        transcript_id="0a1b2c3d",
        recording_name="Долгая встреча.m4a",
        transcript_path=f"{RECORDINGS_FOLDER}/Долгая встреча.json",
        recorded_on="09.11.2026",
        result={"segments": segments},
    )

    content = drafter.draft(kind, transcript)

    assert content.kind == kind
    notes_calls = [call for call in model.calls if call[0] == "notes"]
    assert len(notes_calls) == len(parts)
    assert "Реплика 0." in notes_calls[0][1] and "Реплика 299." in notes_calls[-1][1]
    final_prompt = model.calls[-1][1]
    assert f"конспект {len(parts)}" in final_prompt
    assert "Реплика 0." not in final_prompt
