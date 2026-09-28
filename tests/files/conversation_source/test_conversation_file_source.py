import json
from pathlib import Path

import pytest
from ai_framework import ToolContext

from src.ai_tools.file_take import FileTakeTool, RegisteredFileSource
from src.ai_tools.file_take.tool import FileTakeInput
from src.conversations.errors.attachment_not_downloaded_error import (
    AttachmentNotDownloadedError,
)
from src.conversations.models.attachment_content import AttachmentContent
from src.conversations.models.conversation_attachment import ConversationAttachment
from src.files.sources.conversation_source.conversation_file_source import (
    ConversationFileSource,
)
from src.files.sources.entities.file_request import FileRequest
from src.files.sources.entities.source_file_too_large_error import (
    SourceFileTooLargeError,
)
from src.files.work_folder.work_folder import WorkFolder

LIMIT = 1024
PHOTO = ConversationAttachment(
    attachment_id="7",
    name="IMG-1.jpg",
    media_type="image/jpeg",
    size=4,
    downloaded=True,
)


class FakeChatStore:
    def __init__(self, attachment: ConversationAttachment) -> None:
        self._attachment = attachment
        self.downloads = 0

    def list_attachments(self, message_id: str) -> list[ConversationAttachment]:
        return [self._attachment]

    def fetch_attachment(
        self, message_id: str, attachment_id: str
    ) -> AttachmentContent:
        self.downloads += 1
        if not self._attachment.downloaded:
            raise AttachmentNotDownloadedError(
                self._attachment.name, "открой чат в WhatsApp Desktop и скачай файл"
            )
        return AttachmentContent(
            content=b"\xff\xd8jp",
            name=self._attachment.name,
            media_type=self._attachment.media_type,
        )


def test_attachment_is_fetched_with_origin_label() -> None:
    source = ConversationFileSource(FakeChatStore(PHOTO), "whatsapp", LIMIT)

    fetched = source.fetch(
        FileRequest(thread_id="1", message_id="3EB0AA", attachment_id="7")
    )

    assert fetched.content == b"\xff\xd8jp"
    assert fetched.origin == "whatsapp:3EB0AA/7"


def test_known_size_over_limit_is_refused_without_download() -> None:
    store = FakeChatStore(PHOTO.model_copy(update={"size": LIMIT + 1}))

    with pytest.raises(SourceFileTooLargeError):
        ConversationFileSource(store, "whatsapp", LIMIT).fetch(
            FileRequest(thread_id="1", message_id="3EB0AA", attachment_id="7")
        )

    assert store.downloads == 0


def test_not_downloaded_hint_reaches_model(tmp_path: Path) -> None:
    store = FakeChatStore(PHOTO.model_copy(update={"downloaded": False}))
    tool = FileTakeTool(
        work_files=WorkFolder(tmp_path / "work"),
        sources=[
            RegisteredFileSource(
                "whatsapp",
                "вложение чата",
                ConversationFileSource(store, "whatsapp", LIMIT),
            )
        ],
    )

    result = json.loads(
        tool.execute(
            FileTakeInput(source="whatsapp", message_id="3EB0AA", attachment_id="7"),
            ToolContext({"chat_id": 1, "user_id": 7}),
        )
    )

    assert "скачай файл" in result["error"]
