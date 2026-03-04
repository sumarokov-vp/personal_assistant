import tempfile
from logging import getLogger
from pathlib import Path

from bot_framework import BotMessage, IDocumentDownloader, IMessageReplacer, IMessageSender, check_message_roles
from bot_framework.domain.role_management.repos import RoleRepo

from src.chat.actions.send_to_agent_action import SendToAgentAction

logger = getLogger(__name__)


class PhotoMessageHandler:
    allowed_roles: set[str] | None = {"admin"}

    def __init__(
        self,
        document_downloader: IDocumentDownloader,
        send_to_agent_action: SendToAgentAction,
        message_sender: IMessageSender,
        message_replacer: IMessageReplacer,
        role_repo: RoleRepo,
    ) -> None:
        self.document_downloader = document_downloader
        self.send_to_agent_action = send_to_agent_action
        self.message_sender = message_sender
        self.message_replacer = message_replacer
        self.role_repo = role_repo

    @check_message_roles
    def handle(self, message: BotMessage) -> None:
        if not message.from_user:
            raise ValueError("message.from_user is required but was None")

        original = message.get_original()
        if not original.photo:
            return

        file_id = original.photo[-1].file_id
        file_bytes = self.document_downloader.download_document(file_id)

        suffix = ".jpg"
        tmp_file = tempfile.NamedTemporaryFile(
            delete=False,
            suffix=suffix,
            prefix="photo_",
        )
        tmp_file.write(file_bytes)
        tmp_file.close()

        photo_path = Path(tmp_file.name)
        caption = original.caption or "Фото без подписи"
        agent_text = f"Пользователь отправил фото: {photo_path}\nПодпись: {caption}"

        thinking_msg = self.message_sender.send(
            chat_id=message.chat_id,
            text="Думаю...",
        )

        try:
            self.send_to_agent_action.execute(
                chat_id=message.chat_id,
                user_id=message.from_user.id,
                text=agent_text,
                thinking_message_id=thinking_msg.message_id,
            )
        except Exception as e:
            logger.exception("Agent error on photo")
            self.message_replacer.replace(
                chat_id=message.chat_id,
                message_id=thinking_msg.message_id,
                text=f"Ошибка: {e}",
            )
