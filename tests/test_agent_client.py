from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, MagicMock, patch

from claude_agent_sdk import AssistantMessage, ResultMessage, TextBlock

from src.agent.client import AgentClient


class TestAgentClientSendMessage:
    def test_returns_response_text(self) -> None:
        assistant_msg = MagicMock(spec=AssistantMessage)
        assistant_msg.content = [MagicMock(spec=TextBlock, text="Hello!")]

        async def fake_receive() -> AsyncIterator[MagicMock]:
            yield assistant_msg

        mock_client = AsyncMock()
        mock_client._transport = MagicMock()
        mock_client.query = AsyncMock()
        mock_client.receive_response = fake_receive

        with patch("src.agent.client.ClaudeSDKClient", return_value=mock_client):
            agent = AgentClient()
            result = agent.send_message(user_id=1, text="Hi")

        assert result == "Hello!"
        mock_client.query.assert_awaited_once_with("Hi")

    def test_includes_result_message_text(self) -> None:
        result_msg = MagicMock(spec=ResultMessage)
        result_msg.is_error = False
        result_msg.result = "Final answer"

        async def fake_receive() -> AsyncIterator[MagicMock]:
            yield result_msg

        mock_client = AsyncMock()
        mock_client._transport = MagicMock()
        mock_client.query = AsyncMock()
        mock_client.receive_response = fake_receive

        with patch("src.agent.client.ClaudeSDKClient", return_value=mock_client):
            agent = AgentClient()
            result = agent.send_message(user_id=1, text="Hi")

        assert result == "Final answer"

    def test_returns_empty_when_no_text(self) -> None:
        result_msg = MagicMock(spec=ResultMessage)
        result_msg.is_error = False
        result_msg.result = None

        async def fake_receive() -> AsyncIterator[MagicMock]:
            yield result_msg

        mock_client = AsyncMock()
        mock_client._transport = MagicMock()
        mock_client.query = AsyncMock()
        mock_client.receive_response = fake_receive

        with patch("src.agent.client.ClaudeSDKClient", return_value=mock_client):
            agent = AgentClient()
            result = agent.send_message(user_id=1, text="Hi")

        assert result == ""

    def test_prefers_assistant_message_over_result(self) -> None:
        assistant_msg = MagicMock(spec=AssistantMessage)
        assistant_msg.content = [MagicMock(spec=TextBlock, text="Hello!")]

        result_msg = MagicMock(spec=ResultMessage)
        result_msg.is_error = False
        result_msg.result = "Hello!"

        async def fake_receive() -> AsyncIterator[MagicMock]:
            yield assistant_msg
            yield result_msg

        mock_client = AsyncMock()
        mock_client._transport = MagicMock()
        mock_client.query = AsyncMock()
        mock_client.receive_response = fake_receive

        with patch("src.agent.client.ClaudeSDKClient", return_value=mock_client):
            agent = AgentClient()
            result = agent.send_message(user_id=1, text="Hi")

        assert result == "Hello!"

    def test_raises_on_sdk_error(self) -> None:
        error_msg = MagicMock(spec=ResultMessage)
        error_msg.is_error = True
        error_msg.result = "Something went wrong"

        async def fake_receive() -> AsyncIterator[MagicMock]:
            yield error_msg

        mock_client = AsyncMock()
        mock_client._transport = MagicMock()
        mock_client.query = AsyncMock()
        mock_client.receive_response = fake_receive
        mock_client.disconnect = AsyncMock()

        with patch("src.agent.client.ClaudeSDKClient", return_value=mock_client):
            agent = AgentClient()
            try:
                agent.send_message(user_id=1, text="Hi")
                raised = False
            except RuntimeError as e:
                raised = True
                assert "Something went wrong" in str(e)

        assert raised
