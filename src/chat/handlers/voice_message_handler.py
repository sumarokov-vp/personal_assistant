from logging import getLogger

from bot_framework import (
    BotMessage,
    IMessageDeleter,
    IMessageReplacer,
    IMessageSender,
    check_message_roles,
)
from bot_framework.domain.role_management.repos import RoleRepo

from src.chat.actions.send_to_agent_action import SendToAgentAction
from src.chat.actions.transcribe_voice_action import TranscribeVoiceAction

logger = getLogger(__name__)

TRANSCRIBING_TEXT = "Распознаю речь..."
TRANSCRIPTION_FAILED_TEXT = "Не удалось распознать голосовое сообщение."
NOTHING_HEARD_TEXT = "Не расслышал — в сообщении нет речи."


class VoiceMessageHandler:
    allowed_roles: set[str] | None = {"admin"}

    def __init__(
        self,
        transcribe_voice_action: TranscribeVoiceAction,
        send_to_agent_action: SendToAgentAction,
        message_sender: IMessageSender,
        message_replacer: IMessageReplacer,
        message_deleter: IMessageDeleter,
        role_repo: RoleRepo,
    ) -> None:
        self.transcribe_voice_action = transcribe_voice_action
        self.send_to_agent_action = send_to_agent_action
        self.message_sender = message_sender
        self.message_replacer = message_replacer
        self.message_deleter = message_deleter
        self.role_repo = role_repo

    @check_message_roles
    def handle(self, message: BotMessage) -> None:
        if not message.from_user:
            raise ValueError("message.from_user is required but was None")

        original = message.get_original()
        audio = original.voice or original.audio
        if audio is None:
            return

        status_msg = self.message_sender.send(
            chat_id=message.chat_id, text=TRANSCRIBING_TEXT
        )

        try:
            text = self.transcribe_voice_action.execute(audio.file_id)
        except Exception:
            logger.exception("Voice transcription failed")
            self.message_replacer.replace(
                chat_id=message.chat_id,
                message_id=status_msg.message_id,
                text=TRANSCRIPTION_FAILED_TEXT,
            )
            return

        self.message_deleter.delete(
            chat_id=message.chat_id, message_id=status_msg.message_id
        )

        if not text:
            self.message_sender.send(chat_id=message.chat_id, text=NOTHING_HEARD_TEXT)
            return

        thinking_msg = self.message_sender.send(
            chat_id=message.chat_id, text="Думаю..."
        )

        try:
            self.send_to_agent_action.execute(
                chat_id=message.chat_id,
                user_id=message.from_user.id,
                text=text,
                thinking_message_id=thinking_msg.message_id,
            )
        except Exception as e:
            logger.exception("Agent error on voice")
            self.message_replacer.replace(
                chat_id=message.chat_id,
                message_id=thinking_msg.message_id,
                text=f"Ошибка: {e}",
            )
