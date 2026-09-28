import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from src.conversations.errors.attachment_not_downloaded_error import (
    AttachmentNotDownloadedError,
)
from src.conversations.errors.attachment_not_found_error import (
    AttachmentNotFoundError,
)
from src.conversations.errors.conversation_not_found_error import (
    ConversationNotFoundError,
)
from src.conversations.errors.message_not_found_error import MessageNotFoundError
from src.conversations.models.conversation_window import ConversationWindow
from src.conversations.models.message_query import MessageQuery
from src.conversations.protocols.i_conversation_directory import (
    IConversationDirectory,
)
from src.conversations.protocols.i_conversation_source import IConversationSource
from src.conversations.protocols.i_source_freshness import ISourceFreshness
from src.whatsapp.macos_desktop.errors.whatsapp_schema_error import WhatsAppSchemaError
from src.whatsapp.macos_desktop.errors.whatsapp_snapshot_missing_error import (
    WhatsAppSnapshotMissingError,
)
from src.whatsapp.macos_desktop.services.conversation_source.whatsapp_conversation_source import (
    WhatsAppConversationSource,
)
from tests.whatsapp.macos_desktop.synthetic_snapshot import GROUP, SyntheticSnapshot

TIMEZONE = ZoneInfo("Asia/Almaty")


class Fixture:
    def __init__(self, snapshot_dir: Path) -> None:
        self.snapshot = SyntheticSnapshot(snapshot_dir)
        s = self.snapshot
        self.anna = s.chat("Анна Тестовая", "70000000001@s.whatsapp.net")
        self.group = s.chat("Дача Тест", "120000000000000001@g.us", GROUP)
        self.nameless = s.chat(None, "70000000002@s.whatsapp.net")
        member = s.member(self.group, "Борис Тестов", "70000000003@s.whatsapp.net")

        self.first = s.message(
            self.anna,
            datetime(2026, 9, 1, 9, 0, tzinfo=UTC),
            "Привет, СРОК сдачи отчёта пятница",
        )
        self.reply = s.message(
            self.anna,
            datetime(2026, 9, 1, 9, 5, tzinfo=UTC),
            "Ок, помню про срок",
            from_me=True,
        )
        s.message(
            self.anna, datetime(2026, 9, 1, 9, 6, tzinfo=UTC), None, message_type=6
        )
        self.link_media = s.media(0, title="Заголовок ссылки срок")
        s.message(
            self.anna,
            datetime(2026, 9, 2, 10, 0, tzinfo=UTC),
            "https://example.test",
            media_pk=self.link_media,
        )

        self.document_media = s.media(
            11,
            title="Договор.pdf",
            local_path="Media/70000000001@s.whatsapp.net/a/b/uuid-doc.pdf",
            content=b"%PDF-synthetic",
        )
        self.document = s.message(
            self.anna,
            datetime(2026, 9, 3, 12, 0, tzinfo=UTC),
            None,
            message_type=8,
            media_pk=self.document_media,
        )
        self.photo_media = s.media(52000, title="фото с дачи")
        self.photo = s.message(
            self.group,
            datetime(2026, 9, 4, 8, 0, tzinfo=UTC),
            None,
            member_pk=member,
            message_type=1,
            media_pk=self.photo_media,
        )
        self.group_text = s.message(
            self.group,
            datetime(2026, 9, 4, 8, 30, tzinfo=UTC),
            "Кто везёт уголь?",
            member_pk=member,
            push_name="Боря",
        )
        self.escape_media = s.media(5, local_path="../snapshot_at")
        self.escape = s.message(
            self.nameless,
            datetime(2026, 9, 5, 7, 0, tzinfo=UTC),
            None,
            message_type=8,
            media_pk=self.escape_media,
        )
        s.mark_captured("2026-09-05T07:10:00Z")
        self.source = WhatsAppConversationSource(snapshot_dir, TIMEZONE)


@pytest.fixture
def fx(tmp_path: Path) -> Fixture:
    return Fixture(tmp_path / "whatsapp")


def test_source_satisfies_conversation_protocols(fx: Fixture):
    source: IConversationSource = fx.source
    directory: IConversationDirectory = fx.source
    freshness: ISourceFreshness = fx.source
    assert source is directory is freshness


def test_search_matches_cyrillic_text_case_insensitively_newest_first(fx: Fixture):
    found = fx.source.search(MessageQuery(text="срок"))

    assert [item.message_id for item in found] == [str(fx.reply), str(fx.first)]
    assert found[1].title == "Анна Тестовая"
    assert found[1].sender == "Анна Тестовая"
    assert found[0].sender == "владелец"
    assert found[1].date == "01.09.2026 14:00"


def test_search_by_participant_finds_group_member_messages(fx: Fixture):
    found = fx.source.search(MessageQuery(participant="борис"))

    assert {item.message_id for item in found} == {str(fx.photo), str(fx.group_text)}
    assert {item.sender for item in found} == {"Борис Тестов", "Боря"}


def test_search_by_period_and_conversation(fx: Fixture):
    found = fx.source.search(
        MessageQuery(
            conversation_id=str(fx.anna),
            since=datetime(2026, 9, 2, tzinfo=UTC),
            until=datetime(2026, 9, 4, tzinfo=UTC),
        )
    )

    assert [item.has_attachments for item in found] == [True, False]
    assert found[0].message_id == str(fx.document)


def test_search_caption_of_attachment_and_limit(fx: Fixture):
    assert [
        item.message_id for item in fx.source.search(MessageQuery(text="ФОТО С ДАЧИ"))
    ] == [str(fx.photo)]
    assert len(fx.source.search(MessageQuery(limit=2))) == 2


def test_search_with_foreign_conversation_id_is_not_found(fx: Fixture):
    with pytest.raises(ConversationNotFoundError):
        fx.source.search(MessageQuery(conversation_id="thread-abc"))


def test_read_conversation_window_keeps_latest_and_reports_earlier(fx: Fixture):
    conversation = fx.source.read_conversation(
        str(fx.anna), ConversationWindow(limit=2)
    )

    assert conversation.title == "Анна Тестовая"
    assert not conversation.is_group
    assert [message.date for message in conversation.messages] == [
        "02.09.2026 15:00",
        "03.09.2026 17:00",
    ]
    assert conversation.has_earlier


def test_read_conversation_period_before_first_message_has_nothing_earlier(fx: Fixture):
    conversation = fx.source.read_conversation(
        str(fx.anna), ConversationWindow(until=datetime(2026, 9, 1, 12, tzinfo=UTC))
    )

    assert [message.message_id for message in conversation.messages] == [
        str(fx.first),
        str(fx.reply),
    ]
    assert not conversation.has_earlier
    assert conversation.messages[1].from_owner
    assert conversation.messages[1].recipients == "Анна Тестовая"


def test_read_group_conversation(fx: Fixture):
    conversation = fx.source.read_conversation(str(fx.group), ConversationWindow())

    assert conversation.is_group
    assert conversation.messages[0].text == "фото с дачи"
    assert conversation.messages[0].recipients == "Дача Тест"


def test_read_unknown_conversation_and_message(fx: Fixture):
    with pytest.raises(ConversationNotFoundError):
        fx.source.read_conversation("9999", ConversationWindow())
    with pytest.raises(MessageNotFoundError):
        fx.source.read_message("9999")


def test_list_conversations_includes_groups_and_filters_by_title(fx: Fixture):
    everything = fx.source.list_conversations(None, 10)
    groups = fx.source.list_conversations("дача", 10)

    assert [chat.conversation_id for chat in everything] == [
        str(fx.nameless),
        str(fx.group),
        str(fx.anna),
    ]
    assert everything[0].title == "70000000002"
    assert [(chat.title, chat.is_group) for chat in groups] == [("Дача Тест", True)]
    assert groups[0].last_message_date == "04.09.2026 13:30"


def test_downloaded_attachment_is_listed_and_fetched(fx: Fixture):
    attachments = fx.source.list_attachments(str(fx.document))
    content = fx.source.fetch_attachment(str(fx.document), str(fx.document_media))

    assert [
        (item.name, item.media_type, item.size, item.downloaded) for item in attachments
    ] == [("Договор.pdf", "application/pdf", 11, True)]
    assert content.content == b"%PDF-synthetic"
    assert content.name == "Договор.pdf"


def test_not_downloaded_attachment_asks_owner_to_download_in_desktop(fx: Fixture):
    attachment = fx.source.read_message(str(fx.photo)).attachments[0]

    assert (attachment.name, attachment.media_type, attachment.downloaded) == (
        f"whatsapp-image-{fx.photo_media}.jpg",
        "image/jpeg",
        False,
    )
    with pytest.raises(AttachmentNotDownloadedError, match="WhatsApp Desktop"):
        fx.source.fetch_attachment(str(fx.photo), attachment.attachment_id)


def test_media_path_outside_media_root_is_never_read(fx: Fixture):
    with pytest.raises(AttachmentNotDownloadedError):
        fx.source.fetch_attachment(str(fx.escape), str(fx.escape_media))


def test_link_preview_is_not_an_attachment(fx: Fixture):
    link = fx.source.search(MessageQuery(text="example.test"))[0]

    assert not link.has_attachments
    assert fx.source.list_attachments(link.message_id) == []
    with pytest.raises(AttachmentNotFoundError):
        fx.source.fetch_attachment(link.message_id, str(fx.link_media))


def test_foreign_attachment_id_is_not_found(fx: Fixture):
    with pytest.raises(AttachmentNotFoundError):
        fx.source.fetch_attachment(str(fx.document), str(fx.photo_media))


def test_freshness_reports_last_message_and_capture_time(fx: Fixture):
    freshness = fx.source.freshness()

    assert freshness.last_message_at == datetime(2026, 9, 5, 7, 0, tzinfo=UTC)
    assert freshness.captured_at == datetime(2026, 9, 5, 7, 10, tzinfo=UTC)


def test_missing_snapshot_is_a_clear_error(tmp_path: Path):
    source = WhatsAppConversationSource(tmp_path / "absent", TIMEZONE)

    with pytest.raises(WhatsAppSnapshotMissingError):
        source.freshness()


def test_unknown_schema_is_a_clear_error_not_an_empty_answer(fx: Fixture):
    with closing(sqlite3.connect(fx.snapshot.database_path)) as connection, connection:
        connection.execute("ALTER TABLE ZWAMEDIAITEM DROP COLUMN ZMEDIALOCALPATH")

    with pytest.raises(WhatsAppSchemaError, match="ZMEDIALOCALPATH"):
        fx.source.search(MessageQuery(text="срок"))


def test_snapshot_is_opened_read_only(fx: Fixture):
    before = fx.snapshot.database_path.read_bytes()

    fx.source.search(MessageQuery(text="срок"))
    fx.source.freshness()

    assert fx.snapshot.database_path.read_bytes() == before
    assert sorted(path.name for path in fx.snapshot.snapshot_dir.iterdir()) == [
        "ChatStorage.sqlite",
        "Message",
        "snapshot_at",
    ]
