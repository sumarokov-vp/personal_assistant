import asyncio
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

import src.agent.tools.send_file as send_file_module
from src.agent.tools.registry import SessionRegistry
from src.agent.tools.send_file import init_send_file, send_file
from src.agent.tools.workspace_file_reader import WorkspaceFileReader

_handler = send_file.handler


def _run(coro: Any) -> dict[str, Any]:
    return asyncio.new_event_loop().run_until_complete(coro)


def _setup(workspace: Path) -> MagicMock:
    registry = SessionRegistry()
    document_sender = MagicMock()
    registry.set_context(user_id=1, chat_id=100, document_sender=document_sender)
    init_send_file(registry, WorkspaceFileReader(workspace))
    return document_sender


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir()
    return workspace_dir


@pytest.fixture
def outside_secret(tmp_path: Path) -> Path:
    secret = tmp_path / "id_ed25519"
    secret.write_text("private key")
    return secret


class TestSendFileSuccess:
    def test_sends_file_by_absolute_path(self, workspace: Path) -> None:
        document_sender = _setup(workspace)
        report = workspace / "report.md"
        report.write_text("# Report content")

        result = _run(_handler({"file_path": str(report)}))

        document_sender.send_document.assert_called_once_with(
            chat_id=100, document=b"# Report content", filename="report.md"
        )
        assert result == {"content": [{"type": "text", "text": "File sent successfully: report.md"}]}

    def test_sends_file_by_path_relative_to_workspace(self, workspace: Path) -> None:
        document_sender = _setup(workspace)
        (workspace / "inbox").mkdir()
        (workspace / "inbox" / "photo.jpg").write_bytes(b"jpeg")

        _run(_handler({"file_path": "inbox/photo.jpg"}))

        assert document_sender.send_document.call_args.kwargs["document"] == b"jpeg"


class TestSendFileOutsideWorkspace:
    def test_rejects_absolute_path_outside(self, workspace: Path, outside_secret: Path) -> None:
        document_sender = _setup(workspace)

        with pytest.raises(PermissionError, match="рабочей папки"):
            _run(_handler({"file_path": str(outside_secret)}))

        document_sender.send_document.assert_not_called()

    def test_rejects_parent_traversal(self, workspace: Path, outside_secret: Path) -> None:
        document_sender = _setup(workspace)

        with pytest.raises(PermissionError):
            _run(_handler({"file_path": f"../{outside_secret.name}"}))

        document_sender.send_document.assert_not_called()

    def test_rejects_symlink_pointing_outside(self, workspace: Path, outside_secret: Path) -> None:
        document_sender = _setup(workspace)
        (workspace / "innocent.txt").symlink_to(outside_secret)

        with pytest.raises(PermissionError):
            _run(_handler({"file_path": str(workspace / "innocent.txt")}))

        document_sender.send_document.assert_not_called()

    def test_rejects_symlinked_directory_pointing_outside(
        self, workspace: Path, outside_secret: Path
    ) -> None:
        document_sender = _setup(workspace)
        (workspace / "keys").symlink_to(outside_secret.parent)

        with pytest.raises(PermissionError):
            _run(_handler({"file_path": f"keys/{outside_secret.name}"}))

        document_sender.send_document.assert_not_called()


class TestSendFileNotFound:
    def test_raises_for_missing_file(self, workspace: Path) -> None:
        _setup(workspace)

        with pytest.raises(FileNotFoundError):
            _run(_handler({"file_path": str(workspace / "nonexistent.txt")}))


class TestSendFileNotInitialized:
    def test_raises_when_registry_not_set(self, workspace: Path) -> None:
        send_file_module._registry = None
        (workspace / "test.txt").write_text("content")

        with pytest.raises(ValueError, match="not initialized"):
            _run(_handler({"file_path": str(workspace / "test.txt")}))
