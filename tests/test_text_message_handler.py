from unittest.mock import MagicMock

from bot_framework.entities.bot_message import BotMessage, BotMessageUser
from bot_framework.entities.role import Role
from bot_framework.role_management.repos import RoleRepo

from src.chat.actions.send_to_agent_action import SendToAgentAction
from src.chat.handlers.text_message_handler import TextMessageHandler

ADMIN_ROLE = Role(id=1, name="admin")


def _make_handler(
    action: MagicMock | SendToAgentAction,
    message_service: MagicMock,
) -> TextMessageHandler:
    role_repo = MagicMock(spec=RoleRepo)
    role_repo.get_user_roles.return_value = [ADMIN_ROLE]

    return TextMessageHandler(
        send_to_agent_action=action,
        message_service=message_service,
        role_repo=role_repo,
    )


class TestTextMessageHandlerErrorHandling:
    def test_sends_error_to_chat_on_exception(self) -> None:
        message_service = MagicMock()
        thinking_msg = BotMessage(chat_id=100, message_id=42, text="Думаю...")
        message_service.send.return_value = thinking_msg

        action = MagicMock(spec=SendToAgentAction)
        action.execute.side_effect = RuntimeError("CLI crashed")

        handler = _make_handler(action, message_service)

        message = BotMessage(
            chat_id=100,
            message_id=1,
            text="Привет",
            from_user=BotMessageUser(id=5),
        )

        handler.handle(message)

        message_service.replace.assert_called_once_with(
            chat_id=100,
            message_id=42,
            text="Ошибка: CLI crashed",
        )

    def test_no_error_on_success(self) -> None:
        message_service = MagicMock()
        thinking_msg = BotMessage(chat_id=100, message_id=42, text="Думаю...")
        message_service.send.return_value = thinking_msg

        action = MagicMock(spec=SendToAgentAction)

        handler = _make_handler(action, message_service)

        message = BotMessage(
            chat_id=100,
            message_id=1,
            text="Привет",
            from_user=BotMessageUser(id=5),
        )

        handler.handle(message)

        action.execute.assert_called_once()
        message_service.replace.assert_not_called()
