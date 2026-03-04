from concurrent.futures import ThreadPoolExecutor
from logging import getLogger

from bot_framework import BotCallback, ICallbackAnswerer, IMessageReplacer, IMessageSender, check_roles
from bot_framework.domain.role_management.repos import RoleRepo

from src.chat.handlers.voice_file_storage import VoiceFileStorage
from src.voice_recognition.transcriber import transcribe

logger = getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=2)


class VoiceTranscribeCallbackHandler:
    prefix = "voice_transcribe:"
    allowed_roles: set[str] | None = {"admin"}

    def __init__(
        self,
        callback_answerer: ICallbackAnswerer,
        message_sender: IMessageSender,
        message_replacer: IMessageReplacer,
        role_repo: RoleRepo,
        voice_file_storage: VoiceFileStorage,
    ) -> None:
        self.callback_answerer = callback_answerer
        self.message_sender = message_sender
        self.message_replacer = message_replacer
        self.role_repo = role_repo
        self.voice_file_storage = voice_file_storage

    @check_roles
    def handle(self, callback: BotCallback) -> None:
        self.callback_answerer.answer(callback_query_id=callback.id)

        if not callback.data or not callback.message_id or not callback.message_chat_id:
            return

        prompt_message_id = callback.message_id
        chat_id = callback.message_chat_id

        audio_path = self.voice_file_storage.get(
            chat_id=chat_id,
            message_id=prompt_message_id,
        )
        if audio_path is None:
            self.message_replacer.replace(
                chat_id=chat_id,
                message_id=prompt_message_id,
                text="Файл не найден. Отправьте голосовое сообщение ещё раз.",
            )
            return

        self.message_replacer.replace(
            chat_id=chat_id,
            message_id=prompt_message_id,
            text="Распознавание речи... Это может занять несколько минут.",
        )
        self.voice_file_storage.remove(chat_id=chat_id, message_id=prompt_message_id)

        def run_transcription() -> None:
            try:
                output_path = transcribe(audio_path)
                document = output_path.read_bytes()
                self.message_sender.send_document(
                    chat_id=chat_id,
                    document=document,
                    filename=output_path.name,
                )
                self.message_replacer.replace(
                    chat_id=chat_id,
                    message_id=prompt_message_id,
                    text="Распознавание завершено.",
                )
                output_path.unlink(missing_ok=True)
            except Exception:
                logger.exception("Transcription failed")
                self.message_replacer.replace(
                    chat_id=chat_id,
                    message_id=prompt_message_id,
                    text="Ошибка при распознавании речи.",
                )
            finally:
                audio_path.unlink(missing_ok=True)

        _executor.submit(run_transcription)
