from bot_framework import BotMessage, IMessageSender, check_message_roles
from bot_framework.domain.role_management.repos import RoleRepo

from src.chat.handlers.protocols.i_conversation_clearer import IConversationClearer


class ClearCommandHandler:
    allowed_roles: set[str] | None = {"admin"}

    def __init__(
        self,
        conversation_clearer: IConversationClearer,
        message_sender: IMessageSender,
        role_repo: RoleRepo,
    ) -> None:
        self.conversation_clearer = conversation_clearer
        self.message_sender = message_sender
        self.role_repo = role_repo

    @check_message_roles
    def handle(self, message: BotMessage) -> None:
        if not message.from_user:
            raise ValueError("message.from_user is required but was None")

        self.conversation_clearer.clear_context(str(message.from_user.id))
        self.message_sender.send(
            chat_id=message.chat_id,
            text="Контекст очищен",
        )
