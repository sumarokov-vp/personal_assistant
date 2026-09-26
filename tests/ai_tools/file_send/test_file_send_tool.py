import json
from pathlib import Path
from unittest.mock import Mock

from ai_framework import ToolContext

from src.ai_tools.file_send import FileSendTool
from src.ai_tools.file_send.tool import FileSendInput
from src.dropbox.services.boundary.dropbox_access_policy import DropboxAccessPolicy
from src.dropbox.services.boundary.dropbox_boundary import DropboxBoundary
from src.files.overflow.overflow_folder import OverflowFolder
from src.files.work_folder.work_folder import WorkFolder

OWNER_ID = 555
TELEGRAM_LIMIT = 50 * 1024 * 1024
MEGABYTE = 1024 * 1024
FOREIGN_CHAT_CONTEXT = ToolContext({"chat_id": 999, "user_id": 999})


def build(tmp_path: Path, sender: Mock) -> tuple[FileSendTool, WorkFolder, Path]:
    dropbox = tmp_path / "Dropbox"
    dropbox.mkdir()
    work_folder = WorkFolder(tmp_path / "work")
    tool = FileSendTool(
        work_files=work_folder,
        sender=sender,
        owner_chat_id=OWNER_ID,
        size_limit_bytes=TELEGRAM_LIMIT,
        overflow=OverflowFolder(
            DropboxBoundary(dropbox, DropboxAccessPolicy()), work_folder
        ),
    )
    return tool, work_folder, dropbox


def test_small_file_goes_to_owner_chat_only(tmp_path: Path) -> None:
    sender = Mock()
    tool, work_folder, _ = build(tmp_path, sender)
    content = b"x" * MEGABYTE
    work_file = work_folder.put(content, "passport.pdf", "application/pdf", "dropbox")

    output = json.loads(
        tool.execute(FileSendInput(file_id=work_file.id), FOREIGN_CHAT_CONTEXT)
    )

    assert output == {"sent": True, "name": "passport.pdf"}
    sender.send_document.assert_called_once_with(
        chat_id=OWNER_ID, document=content, filename="passport.pdf"
    )


def test_file_over_telegram_limit_lands_in_overflow_folder(tmp_path: Path) -> None:
    sender = Mock()
    tool, work_folder, dropbox = build(tmp_path, sender)
    content = b"v" * (60 * MEGABYTE)
    work_file = work_folder.put(content, "video.mp4", "video/mp4", "mail")

    output = json.loads(
        tool.execute(FileSendInput(file_id=work_file.id), FOREIGN_CHAT_CONTEXT)
    )

    sender.send_document.assert_not_called()
    assert output["sent"] is False
    assert output["path"] == "Personal Assistant/video.mp4"
    assert (dropbox / "Personal Assistant" / "video.mp4").stat().st_size == len(content)


def test_large_file_without_dropbox_is_an_error(tmp_path: Path) -> None:
    sender = Mock()
    work_folder = WorkFolder(tmp_path / "work")
    tool = FileSendTool(
        work_files=work_folder,
        sender=sender,
        owner_chat_id=OWNER_ID,
        size_limit_bytes=10,
        overflow=None,
    )
    work_file = work_folder.put(
        b"x" * 11, "big.bin", "application/octet-stream", "chat"
    )

    output = json.loads(
        tool.execute(FileSendInput(file_id=work_file.id), FOREIGN_CHAT_CONTEXT)
    )

    sender.send_document.assert_not_called()
    assert "error" in output


def test_unknown_file_id_is_an_error(tmp_path: Path) -> None:
    sender = Mock()
    tool, _, _ = build(tmp_path, sender)

    output = json.loads(
        tool.execute(FileSendInput(file_id="deadbeef"), FOREIGN_CHAT_CONTEXT)
    )

    sender.send_document.assert_not_called()
    assert "error" in output
