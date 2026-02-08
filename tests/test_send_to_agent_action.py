from unittest.mock import MagicMock

from src.chat.actions.send_to_agent_action import SendToAgentAction


class TestSendToAgentActionEmptyResponse:
    def test_replaces_empty_response_with_fallback(self) -> None:
        agent_client = MagicMock()
        agent_client.send_message.return_value = ""

        message_service = MagicMock()

        action = SendToAgentAction(
            agent_client=agent_client,
            message_service=message_service,
        )

        action.execute(chat_id=100, user_id=1, text="Hi", thinking_message_id=42)

        agent_client.send_message.assert_called_once_with(1, 100, "Hi")

        message_service.replace.assert_called_once_with(
            chat_id=100,
            message_id=42,
            text="Пустой ответ от агента",
        )

    def test_sends_normal_response(self) -> None:
        agent_client = MagicMock()
        agent_client.send_message.return_value = "Hello!"

        message_service = MagicMock()

        action = SendToAgentAction(
            agent_client=agent_client,
            message_service=message_service,
        )

        action.execute(chat_id=100, user_id=1, text="Hi", thinking_message_id=42)

        agent_client.send_message.assert_called_once_with(1, 100, "Hi")

        message_service.replace.assert_called_once_with(
            chat_id=100,
            message_id=42,
            text="Hello!",
        )
