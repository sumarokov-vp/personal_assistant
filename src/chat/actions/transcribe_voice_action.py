from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from logging import getLogger
from pathlib import Path

from bot_framework import IDocumentSender, IMessageReplacer

from src.chat.actions.protocols.i_transcriber import ITranscriber
from src.chat.actions.protocols.i_transcript_cleaner import ITranscriptCleaner

logger = getLogger(__name__)


class TranscribeVoiceAction:
    def __init__(
        self,
        transcriber: ITranscriber,
        transcript_cleaner: ITranscriptCleaner,
        document_sender: IDocumentSender,
        message_replacer: IMessageReplacer,
    ) -> None:
        self.transcriber = transcriber
        self.transcript_cleaner = transcript_cleaner
        self.document_sender = document_sender
        self.message_replacer = message_replacer
        self._executor = ThreadPoolExecutor(max_workers=2)

    def execute(self, chat_id: int, audio_path: Path, status_message_id: int) -> None:
        self._executor.submit(self._run, chat_id, audio_path, status_message_id)

    def _run(self, chat_id: int, audio_path: Path, status_message_id: int) -> None:
        try:
            raw_text = self.transcriber(audio_path)
            clean_text = self.transcript_cleaner.clean(raw_text)
            document = _build_document(clean_text)
            self.document_sender.send_document(
                chat_id=chat_id,
                document=document,
                filename=_build_filename(),
            )
            self.message_replacer.replace(
                chat_id=chat_id,
                message_id=status_message_id,
                text="Готово.",
            )
        except Exception:
            logger.exception("Voice transcription failed")
            self.message_replacer.replace(
                chat_id=chat_id,
                message_id=status_message_id,
                text="Не удалось распознать голосовое сообщение.",
            )
        finally:
            audio_path.unlink(missing_ok=True)


def _build_document(text: str) -> bytes:
    # BOM нужен, чтобы мобильный Telegram распознал UTF-8 в превью документа,
    # иначе кириллица отображается «каракулями».
    return text.encode("utf-8-sig")


def _build_filename() -> str:
    timestamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
    return f"transcript_{timestamp}.md"
