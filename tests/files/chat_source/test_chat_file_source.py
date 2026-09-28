import pytest
from ai_framework import Attachment
from ai_framework.attachments.in_memory_attachment_store import InMemoryAttachmentStore
from ai_framework.entities.message import Message

from src.files.sources.chat_attachments.chat_attachments import ChatAttachments
from src.files.sources.chat_source.chat_file_source import ChatFileSource
from src.files.sources.entities.file_request import FileRequest
from src.files.sources.entities.source_file_not_found_error import (
    SourceFileNotFoundError,
)

THREAD = "42"
OLD_PHOTO_KEY = "attachments/dc1f3dd8aa11bb22cc33dd44ee55ff66.jpg"
NEW_PHOTO_KEY = "attachments/d69eed2c0011223344556677889900aa.jpg"


class InMemoryHistory:
    def __init__(self, messages: list[Message]) -> None:
        self._messages = messages

    def get_messages(self, thread_id: str) -> list[Message]:
        return self._messages


class KeyedStore:
    def __init__(self, objects: dict[str, bytes]) -> None:
        self._objects = objects

    def get(self, key: str) -> bytes:
        return self._objects[key]


def _photo_turn(key: str) -> Message:
    return Message(
        role="user",
        content="",
        attachments=[Attachment(media_type="image/jpeg", filename=None, key=key)],
    )


def _chatter(turns: int) -> list[Message]:
    return [
        message
        for _ in range(turns)
        for message in (
            Message(role="user", content="ещё вопрос"),
            Message(role="assistant", content="ответ"),
        )
    ]


def _source() -> ChatFileSource:
    history = InMemoryHistory(
        [_photo_turn(OLD_PHOTO_KEY), *_chatter(15), _photo_turn(NEW_PHOTO_KEY)]
    )
    store = KeyedStore({OLD_PHOTO_KEY: b"old", NEW_PHOTO_KEY: b"new"})
    return ChatFileSource(ChatAttachments(history, store), max_bytes=1024)


@pytest.mark.parametrize(
    "address",
    [
        "photo_dc1f3dd8.jpg",
        "PHOTO_DC1F3DD8.JPG",
        OLD_PHOTO_KEY,
        "dc1f3dd8aa11bb22cc33dd44ee55ff66.jpg",
    ],
)
def test_unnamed_photo_older_than_ten_turns_is_found_by_name_or_key(
    address: str,
) -> None:
    fetched = _source().fetch(FileRequest(thread_id=THREAD, name=address))

    assert fetched.content == b"old"
    assert fetched.name == "photo_dc1f3dd8.jpg"


def test_without_name_takes_newest() -> None:
    assert _source().fetch(FileRequest(thread_id=THREAD, name=None)).content == b"new"


def test_miss_lists_addressable_names() -> None:
    with pytest.raises(
        SourceFileNotFoundError, match="photo_d69eed2c.jpg, photo_dc1f3dd8.jpg"
    ):
        _source().fetch(FileRequest(thread_id=THREAD, name="1.jpg"))


def test_named_document_found_by_original_name() -> None:
    store = InMemoryAttachmentStore()
    key = store.put(b"pdf", "application/pdf")
    history = InMemoryHistory(
        [
            Message(
                role="user",
                content="",
                attachments=[
                    Attachment(
                        media_type="application/pdf", filename="Акт.pdf", key=key
                    )
                ],
            )
        ]
    )

    fetched = ChatFileSource(ChatAttachments(history, store), 1024).fetch(
        FileRequest(thread_id=THREAD, name="акт.pdf")
    )

    assert fetched.content == b"pdf"
