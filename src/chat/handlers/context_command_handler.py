from bot_framework.decorators import check_message_roles
from bot_framework.entities.bot_message import BotMessage
from bot_framework.protocols.i_message_service import IMessageService
from bot_framework.role_management.repos import RoleRepo
from src.agent.protocols.i_agent_client import IAgentClient


class ContextCommandHandler:
    allowed_roles: set[str] | None = {"admin"}

    def __init__(
        self,
        agent_client: IAgentClient,
        message_service: IMessageService,
        role_repo: RoleRepo,
    ) -> None:
        self.agent_client = agent_client
        self.message_service = message_service
        self.role_repo = role_repo

    @check_message_roles
    def handle(self, message: BotMessage) -> None:
        if not message.from_user:
            raise ValueError("message.from_user is required but was None")

        context = self.agent_client.get_context(message.from_user.id)
        self.message_service.send(
            chat_id=message.chat_id,
            text=context,
        )
