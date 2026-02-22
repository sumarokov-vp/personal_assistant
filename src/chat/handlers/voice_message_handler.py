import tempfile
from pathlib import Path

from bot_framework.decorators import check_message_roles
from bot_framework.entities.bot_message import BotMessage
from bot_framework.entities.button import Button
from bot_framework.entities.keyboard import Keyboard
from bot_framework.protocols.i_message_sender import IMessageSender
from bot_framework.role_management.repos import RoleRepo
from telebot import TeleBot

from src.chat.handlers.voice_file_storage import VoiceFileStorage


class VoiceMessageHandler:
    allowed_roles: set[str] | None = {"admin"}

    def __init__(
        self,
        bot: TeleBot,
        message_sender: IMessageSender,
        role_repo: RoleRepo,
        voice_file_storage: VoiceFileStorage,
    ) -> None:
        self.bot = bot
        self.message_sender = message_sender
        self.role_repo = role_repo
        self.voice_file_storage = voice_file_storage

    @check_message_roles
    def handle(self, message: BotMessage) -> None:
        original = message.get_original()

        if original.voice:
            file_id = original.voice.file_id
        elif original.audio:
            file_id = original.audio.file_id
        else:
            return

        file_info = self.bot.get_file(file_id)
        if not file_info.file_path:
            return
        file_bytes = self.bot.download_file(file_info.file_path)

        suffix = Path(file_info.file_path).suffix or ".ogg"
        tmp_file = tempfile.NamedTemporaryFile(
            delete=False,
            suffix=suffix,
            prefix="voice_",
        )
        tmp_file.write(file_bytes)
        tmp_file.close()

        audio_path = Path(tmp_file.name)

        keyboard = Keyboard(
            rows=[
                [
                    Button(
                        text="Распознать",
                        callback_data=f"voice_transcribe:{message.message_id}",
                    )
                ]
            ]
        )

        prompt_message = self.message_sender.send(
            chat_id=message.chat_id,
            text="Голосовое сообщение получено. Распознать речь?",
            keyboard=keyboard,
        )

        self.voice_file_storage.save(
            chat_id=message.chat_id,
            message_id=prompt_message.message_id,
            file_path=audio_path,
        )
