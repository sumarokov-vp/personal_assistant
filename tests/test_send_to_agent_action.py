from typing import Any
from unittest.mock import MagicMock

import pytest
from bot_framework import BotMessage, BotMessageUser, Role
from bot_framework.domain.role_management.repos import RoleRepo
from ai_framework import AIApplication, AIResponse, Message, Provider
from ai_framework.entities.tool import ToolCall
from ai_framework.infrastructure_factory import InfrastructureContext
from ai_framework.memory.in_memory_store import InMemoryStore
from ai_framework.protocols.base_tool import BaseTool
from ai_framework.session.in_memory_session_store import InMemorySessionStore

from src.chat.actions.send_to_agent_action import EMPTY_RESPONSE_TEXT, SendToAgentAction
from src.chat.handlers.text_message_handler import TextMessageHandler


class ScriptedProvider:
    def __init__(self, replies: list[AIResponse]) -> None:
        self.replies = replies
        self.calls: list[tuple[list[Message], str | None]] = []

    def send_message(
        self,
        messages: list[Message],
        system: str | None = None,
        tools: list[BaseTool] | None = None,
        tool_context: dict[str, Any] | None = None,
        thread_id: str | None = None,
    ) -> AIResponse:
        self.calls.append((list(messages), system))
        return self.replies.pop(0)


class DatedPromptBuilder:
    def __init__(self) -> None:
        self.built = 0

    def build(self) -> str:
        self.built += 1
        return f"prompt #{self.built}"


def _ai_application(monkeypatch: pytest.MonkeyPatch, provider: ScriptedProvider) -> AIApplication:
    monkeypatch.setattr("ai_framework.application.create_provider", lambda *_args: provider)
    monkeypatch.setattr(
        "ai_framework.application.open_infrastructure",
        lambda _url: InfrastructureContext(memory=InMemoryStore(), sessions=InMemorySessionStore()),
    )
    return AIApplication(
        api_key="test",
        provider=Provider.CLAUDE_SDK,
        system_prompt="initial",
        database_url="postgres://unused",
        tools=[],
        history_turns_limit=10,
    )


def _action(ai: Any, prompt_builder: DatedPromptBuilder) -> tuple[SendToAgentAction, MagicMock, MagicMock, MagicMock]:
    message_sender = MagicMock()
    message_replacer = MagicMock()
    message_deleter = MagicMock()
    action = SendToAgentAction(
        ai=ai,
        system_prompt_builder=prompt_builder,
        message_sender=message_sender,
        message_replacer=message_replacer,
        message_deleter=message_deleter,
    )
    return action, message_sender, message_replacer, message_deleter


class TestTextThroughAIApplication:
    def test_owner_text_reaches_model_and_reply_lands_in_chat(self, monkeypatch: pytest.MonkeyPatch) -> None:
        provider = ScriptedProvider([AIResponse(content="Привет! Чем помочь?")])
        prompt_builder = DatedPromptBuilder()
        with _ai_application(monkeypatch, provider) as ai:
            action, sender, replacer, _deleter = _action(ai, prompt_builder)
            sender.send.return_value = BotMessage(chat_id=100, message_id=42, text="Думаю...")
            role_repo = MagicMock(spec=RoleRepo)
            role_repo.get_user_roles.return_value = [Role(id=1, name="admin")]
            handler = TextMessageHandler(
                send_to_agent_action=action,
                message_sender=sender,
                message_replacer=replacer,
                role_repo=role_repo,
            )
            handler.handle(BotMessage(chat_id=100, message_id=1, text="Привет", from_user=BotMessageUser(id=5)))

        messages, system = provider.calls[0]
        assert [(m.role, m.content) for m in messages] == [("user", "Привет")]
        assert system == "prompt #1"
        replacer.replace.assert_called_once_with(chat_id=100, message_id=42, text="Привет! Чем помочь?")

    def test_second_message_carries_history_and_fresh_prompt(self, monkeypatch: pytest.MonkeyPatch) -> None:
        provider = ScriptedProvider([AIResponse(content="Первый"), AIResponse(content="Второй")])
        prompt_builder = DatedPromptBuilder()
        with _ai_application(monkeypatch, provider) as ai:
            action, _sender, _replacer, _deleter = _action(ai, prompt_builder)
            action.execute(chat_id=100, user_id=5, text="раз", thinking_message_id=1)
            action.execute(chat_id=100, user_id=5, text="два", thinking_message_id=2)

        messages, system = provider.calls[1]
        assert [m.content for m in messages] == ["раз", "Первый", "два"]
        assert system == "prompt #2"

    def test_clear_context_forgets_history(self, monkeypatch: pytest.MonkeyPatch) -> None:
        provider = ScriptedProvider([AIResponse(content="Первый"), AIResponse(content="Второй")])
        with _ai_application(monkeypatch, provider) as ai:
            action, _sender, _replacer, _deleter = _action(ai, DatedPromptBuilder())
            action.execute(chat_id=100, user_id=5, text="раз", thinking_message_id=1)
            ai.clear_context("5")
            action.execute(chat_id=100, user_id=5, text="два", thinking_message_id=2)

        messages, _system = provider.calls[1]
        assert [m.content for m in messages] == ["два"]


class TestSendToAgentActionReplies:
    def test_empty_response_replaced_with_fallback(self) -> None:
        ai = MagicMock()
        ai.process_message.return_value = AIResponse(content="  ")
        action, _sender, replacer, _deleter = _action(ai, DatedPromptBuilder())

        action.execute(chat_id=100, user_id=1, text="Hi", thinking_message_id=42)

        replacer.replace.assert_called_once_with(chat_id=100, message_id=42, text=EMPTY_RESPONSE_TEXT)

    def test_suppressed_response_removes_thinking_message(self) -> None:
        ai = MagicMock()
        ai.process_message.return_value = AIResponse(
            content=None,
            tool_calls=[ToolCall(id="1", name="t", arguments={})],
            suppress_response=True,
        )
        action, _sender, replacer, deleter = _action(ai, DatedPromptBuilder())

        action.execute(chat_id=100, user_id=1, text="Hi", thinking_message_id=42)

        deleter.delete.assert_called_once_with(chat_id=100, message_id=42)
        replacer.replace.assert_not_called()

    def test_long_response_split_into_chunks(self) -> None:
        ai = MagicMock()
        ai.process_message.return_value = AIResponse(content="a" * 4000 + "\n" + "b" * 200)
        action, sender, replacer, _deleter = _action(ai, DatedPromptBuilder())

        action.execute(chat_id=100, user_id=1, text="Hi", thinking_message_id=42)

        replacer.replace.assert_called_once_with(chat_id=100, message_id=42, text="a" * 4000)
        sender.send.assert_called_once_with(chat_id=100, text="b" * 200)
