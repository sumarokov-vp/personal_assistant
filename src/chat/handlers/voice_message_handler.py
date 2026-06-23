import tempfile
from pathlib import Path

from bot_framework import BotMessage, IDocumentDownloader, IMessageSender, check_message_roles
from bot_framework.domain.role_management.repos import RoleRepo

from src.chat.actions.transcribe_voice_action import TranscribeVoiceAction


class VoiceMessageHandler:
    allowed_roles: set[str] | None = {"admin", "voice_recognition"}

    def __init__(
        self,
        document_downloader: IDocumentDownloader,
        transcribe_voice_action: TranscribeVoiceAction,
        message_sender: IMessageSender,
        role_repo: RoleRepo,
    ) -> None:
        self.document_downloader = document_downloader
        self.transcribe_voice_action = transcribe_voice_action
        self.message_sender = message_sender
        self.role_repo = role_repo

    @check_message_roles
    def handle(self, message: BotMessage) -> None:
        original = message.get_original()

        if original.voice:
            file_id = original.voice.file_id
        elif original.audio:
            file_id = original.audio.file_id
        else:
            return

        file_bytes = self.document_downloader.download_document(file_id)

        tmp_file = tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".ogg",
            prefix="voice_",
        )
        tmp_file.write(file_bytes)
        tmp_file.close()

        audio_path = Path(tmp_file.name)

        status_message = self.message_sender.send(
            chat_id=message.chat_id,
            text="Распознаю речь... Это займёт минуту.",
        )

        self.transcribe_voice_action.execute(
            chat_id=message.chat_id,
            audio_path=audio_path,
            status_message_id=status_message.message_id,
        )
