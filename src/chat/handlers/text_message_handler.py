from logging import getLogger

from bot_framework.decorators import check_message_roles
from bot_framework.entities.bot_message import BotMessage
from bot_framework.protocols.i_message_service import IMessageService
from bot_framework.role_management.repos import RoleRepo
from src.chat.actions.send_to_agent_action import SendToAgentAction

logger = getLogger(__name__)


class TextMessageHandler:
    allowed_roles: set[str] | None = {"admin"}

    def __init__(
        self,
        send_to_agent_action: SendToAgentAction,
        message_service: IMessageService,
        role_repo: RoleRepo,
    ) -> None:
        self.send_to_agent_action = send_to_agent_action
        self.message_service = message_service
        self.role_repo = role_repo

    @check_message_roles
    def handle(self, message: BotMessage) -> None:
        if not message.from_user:
            raise ValueError("message.from_user is required but was None")

        if not message.text:
            return

        thinking_msg = self.message_service.send(
            chat_id=message.chat_id,
            text="Думаю...",
        )

        try:
            self.send_to_agent_action.execute(
                chat_id=message.chat_id,
                user_id=message.from_user.id,
                text=message.text,
                thinking_message_id=thinking_msg.message_id,
            )
        except Exception as e:
            logger.exception("Agent error")
            error_text = f"Ошибка: {e}"
            self.message_service.replace(
                chat_id=message.chat_id,
                message_id=thinking_msg.message_id,
                text=error_text,
            )
