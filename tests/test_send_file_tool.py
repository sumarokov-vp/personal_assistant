import asyncio
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import src.agent.tools.send_file as send_file_module
from src.agent.tools.registry import SessionRegistry
from src.agent.tools.send_file import init_send_file, send_file

_handler = send_file.handler


def _run(coro: object) -> dict[str, Any]:
    return asyncio.new_event_loop().run_until_complete(coro)  # type:ignore[arg-type]


def _setup_registry(tmp_path: Path) -> tuple[SessionRegistry, MagicMock]:
    registry = SessionRegistry()
    bot = MagicMock()
    registry.set_context(user_id=1, chat_id=100, bot=bot)
    init_send_file(registry)
    return registry, bot


class TestSendFileSuccess:
    def test_sends_existing_file(self, tmp_path: Path) -> None:
        _registry, bot = _setup_registry(tmp_path)
        test_file = tmp_path / "report.md"
        test_file.write_text("# Report content")

        result = _run(_handler({"file_path": str(test_file)}))

        bot.send_document.assert_called_once()
        call_args = bot.send_document.call_args
        assert call_args[0][0] == 100
        assert result == {
            "content": [{"type": "text", "text": "File sent successfully: report.md"}]
        }


class TestSendFileNotFound:
    def test_returns_error_for_missing_file(self, tmp_path: Path) -> None:
        _setup_registry(tmp_path)
        missing_file = tmp_path / "nonexistent.txt"

        result = _run(_handler({"file_path": str(missing_file)}))

        assert result["isError"] is True
        assert "File not found" in result["content"][0]["text"]


class TestSendFileNotInitialized:
    def test_raises_when_registry_not_set(self, tmp_path: Path) -> None:
        send_file_module._registry = None
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        raised = False
        try:
            _run(_handler({"file_path": str(test_file)}))
        except ValueError as e:
            raised = True
            assert "not initialized" in str(e)

        assert raised
