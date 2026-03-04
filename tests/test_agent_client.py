import asyncio
import threading
from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, MagicMock

from claude_agent_sdk import AssistantMessage, ResultMessage, TextBlock

from src.agent.client import AgentClient
from src.agent.tools.registry import SessionRegistry


def _create_loop() -> asyncio.AbstractEventLoop:
    loop = asyncio.new_event_loop()
    thread = threading.Thread(target=loop.run_forever, daemon=True)
    thread.start()
    return loop


def _create_agent() -> tuple[AgentClient, MagicMock]:
    pool = MagicMock()
    pool.loop = _create_loop()
    agent = AgentClient(
        pool=pool, session_registry=SessionRegistry(), document_sender=MagicMock()
    )
    return agent, pool


def _make_result_message(
    *, is_error: bool = False, result: str | None = None
) -> MagicMock:
    msg = MagicMock(spec=ResultMessage)
    msg.is_error = is_error
    msg.result = result
    msg.num_turns = 1
    msg.total_cost_usd = 0.001
    msg.duration_ms = 100
    return msg


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

        agent, pool = _create_agent()
        pool.get_or_create.return_value = mock_client
        result = agent.send_message(user_id=1, chat_id=100, text="Hi")

        assert result == "Hello!"
        mock_client.query.assert_awaited_once_with("Hi")

    def test_includes_result_message_text(self) -> None:
        result_msg = _make_result_message(result="Final answer")

        async def fake_receive() -> AsyncIterator[MagicMock]:
            yield result_msg

        mock_client = AsyncMock()
        mock_client._transport = MagicMock()
        mock_client.query = AsyncMock()
        mock_client.receive_response = fake_receive

        agent, pool = _create_agent()
        pool.get_or_create.return_value = mock_client
        result = agent.send_message(user_id=1, chat_id=100, text="Hi")

        assert result == "Final answer"

    def test_returns_empty_when_no_text(self) -> None:
        result_msg = _make_result_message(result=None)

        async def fake_receive() -> AsyncIterator[MagicMock]:
            yield result_msg

        mock_client = AsyncMock()
        mock_client._transport = MagicMock()
        mock_client.query = AsyncMock()
        mock_client.receive_response = fake_receive

        agent, pool = _create_agent()
        pool.get_or_create.return_value = mock_client
        result = agent.send_message(user_id=1, chat_id=100, text="Hi")

        assert result == ""

    def test_prefers_assistant_message_over_result(self) -> None:
        assistant_msg = MagicMock(spec=AssistantMessage)
        assistant_msg.content = [MagicMock(spec=TextBlock, text="Hello!")]

        result_msg = _make_result_message(result="Hello!")

        async def fake_receive() -> AsyncIterator[MagicMock]:
            yield assistant_msg
            yield result_msg

        mock_client = AsyncMock()
        mock_client._transport = MagicMock()
        mock_client.query = AsyncMock()
        mock_client.receive_response = fake_receive

        agent, pool = _create_agent()
        pool.get_or_create.return_value = mock_client
        result = agent.send_message(user_id=1, chat_id=100, text="Hi")

        assert result == "Hello!"

    def test_raises_on_sdk_error(self) -> None:
        error_msg = _make_result_message(
            is_error=True, result="Something went wrong"
        )

        async def fake_receive() -> AsyncIterator[MagicMock]:
            yield error_msg

        mock_client = AsyncMock()
        mock_client._transport = MagicMock()
        mock_client.query = AsyncMock()
        mock_client.receive_response = fake_receive
        mock_client.disconnect = AsyncMock()

        agent, pool = _create_agent()
        pool.get_or_create.return_value = mock_client
        try:
            agent.send_message(user_id=1, chat_id=100, text="Hi")
            raised = False
        except RuntimeError as e:
            raised = True
            assert "Something went wrong" in str(e)

        assert raised
