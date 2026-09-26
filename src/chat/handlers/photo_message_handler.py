from bot_framework import BotMessage, IMessageSender, check_message_roles
from bot_framework.domain.role_management.repos import RoleRepo

PHOTO_TOO_LARGE_TEXT = "Фото больше 10 МБ — такое не читаю."
PHOTO_NOT_READY_TEXT = "Фото пока не читаю — скоро научусь."


class PhotoMessageHandler:
    allowed_roles: set[str] | None = {"admin"}

    def __init__(
        self,
        message_sender: IMessageSender,
        role_repo: RoleRepo,
        max_file_bytes: int,
    ) -> None:
        self.message_sender = message_sender
        self.role_repo = role_repo
        self.max_file_bytes = max_file_bytes

    @check_message_roles
    def handle(self, message: BotMessage) -> None:
        if not message.from_user:
            raise ValueError("message.from_user is required but was None")

        original = message.get_original()
        if not original.photo:
            return

        largest_photo = original.photo[-1]
        if (largest_photo.file_size or 0) > self.max_file_bytes:
            self.message_sender.send(chat_id=message.chat_id, text=PHOTO_TOO_LARGE_TEXT)
            return

        self._send_image(message)

    def _send_image(self, message: BotMessage) -> None:
        self.message_sender.send(chat_id=message.chat_id, text=PHOTO_NOT_READY_TEXT)
