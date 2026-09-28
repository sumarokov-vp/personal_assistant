import json
import logging
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from ai_framework import ToolContext
from ai_framework.attachments.in_memory_attachment_store import InMemoryAttachmentStore
from ai_framework.entities.message import Message

from src.ai_tools.case_add_event.tool import CaseAddEventInput
from src.ai_tools.file_take.tool import FileTakeInput
from src.ai_tools.list_telegram_chats.tool import (
    ListTelegramChatsInput,
    ListTelegramChatsTool,
)
from src.ai_tools.read_telegram.tool import ReadTelegramInput, ReadTelegramTool
from src.ai_tools.search_telegram.tool import SearchTelegramInput, SearchTelegramTool
from src.ai_tools.telegram_common import UntrustedTelegramFrame
from src.chat.actions.system_prompt_builder import SystemPromptBuilder
from src.files.sources.chat_attachments.chat_attachments import ChatAttachments
from src.files.work_folder.work_folder import WorkFolder
from tests.ai_tools.telegram.fake_telegram_source import (
    GROUP_MESSAGE,
    PRIVATE_MESSAGE,
    SUPERGROUP_ID,
    FakeTelegramSource,
)
from workers.bot.file_tools_factory import build_file_take_tool
from workers.bot.telegram_tools_factory import (
    bot_conversation_id,
    build_telegram_source,
    build_telegram_tools,
)

TIMEZONE = ZoneInfo("Asia/Almaty")
ASSISTANT_BOT_CREDENTIAL = "7001:synthetic"
CONTEXT = ToolContext({"chat_id": 1, "user_id": 7})
SYSTEM_PROMPT = Path(__file__).parents[3] / "data" / "system_prompt.txt"
TELEGRAM_TOOL_NAMES = ("search_telegram", "read_telegram", "list_telegram_chats")


class EmptyHistory:
    def get_messages(self, thread_id: str) -> list[Message]:
        return []


def _search(source: FakeTelegramSource) -> SearchTelegramTool:
    return SearchTelegramTool(source, UntrustedTelegramFrame(), TIMEZONE)


def _read(source: FakeTelegramSource) -> ReadTelegramTool:
    return ReadTelegramTool(source, UntrustedTelegramFrame(), TIMEZONE)


def _prompt(connectors: tuple[str, ...]) -> str:
    return SystemPromptBuilder(
        template=SYSTEM_PROMPT.read_text(encoding="utf-8"),
        timezone=TIMEZONE,
        connectors=connectors,
    ).build()


def test_search_frames_text_and_shows_link() -> None:
    source = FakeTelegramSource()
    tool = _search(source)

    result = tool.execute(SearchTelegramInput(text="Договор"), CONTEXT)

    assert "<untrusted_telegram boundary=" in result
    assert f"id: {GROUP_MESSAGE.message_id}" in result
    assert "ссылка: https://t.me/c/1234567890/42" in result
    assert source.queries[0].text == "Договор"


def test_search_without_any_filter_asks_for_one_and_skips_telegram() -> None:
    source = FakeTelegramSource()
    tool = _search(source)

    result = tool.execute(SearchTelegramInput(text="  "), CONTEXT)

    assert "participant" in result
    assert source.queries == []


def test_read_message_of_supergroup_gives_link_and_attachment() -> None:
    tool = _read(FakeTelegramSource())

    result = tool.execute(
        ReadTelegramInput(message_id=GROUP_MESSAGE.message_id), CONTEXT
    )

    assert "Ссылка на сообщение: https://t.me/c/1234567890/42" in result
    assert "attachment_id: 5550001" in result
    assert "2.0 МБ" in result


def test_read_message_of_private_chat_says_there_is_no_link() -> None:
    tool = _read(FakeTelegramSource())

    result = tool.execute(
        ReadTelegramInput(message_id=PRIVATE_MESSAGE.message_id), CONTEXT
    )

    assert "Ссылки на сообщение у этого чата нет." in result
    assert "t.me" not in result


def test_read_needs_exactly_one_id() -> None:
    tool = _read(FakeTelegramSource())

    result = tool.execute(ReadTelegramInput(), CONTEXT)

    assert "ровно одно" in result


def test_read_chat_and_list_chats_use_negative_chat_ids() -> None:
    source = FakeTelegramSource()

    chat = _read(source).execute(ReadTelegramInput(chat_id=SUPERGROUP_ID), CONTEXT)
    listing = ListTelegramChatsTool(source, UntrustedTelegramFrame()).execute(
        ListTelegramChatsInput(), CONTEXT
    )

    assert "(группа, chat_id -1001234567890)" in chat
    assert "chat_id -1001234567890 · Стройка дачи · группа" in listing


def test_message_id_must_name_chat_and_message() -> None:
    with pytest.raises(ValueError):
        ReadTelegramInput(message_id="42")


def test_file_take_telegram_marks_origin(tmp_path: Path) -> None:
    tool = build_file_take_tool(
        WorkFolder(tmp_path / "work"),
        ChatAttachments(EmptyHistory(), InMemoryAttachmentStore()),
        None,
        None,
        telegram=FakeTelegramSource(),
    )

    taken = json.loads(
        tool.execute(
            FileTakeInput(
                source="telegram",
                message_id=GROUP_MESSAGE.message_id,
                attachment_id="5550001",
            ),
            CONTEXT,
        )
    )

    meta = json.loads(
        (tmp_path / "work" / taken["file_id"] / ".work_file.json").read_text()
    )
    assert taken["name"] == "contract.pdf"
    assert meta["source"] == f"telegram:{GROUP_MESSAGE.message_id}/5550001"


def test_file_take_has_no_telegram_source_without_connector(tmp_path: Path) -> None:
    tool = build_file_take_tool(
        WorkFolder(tmp_path / "work"),
        ChatAttachments(EmptyHistory(), InMemoryAttachmentStore()),
        None,
        None,
    )

    assert "telegram" not in json.dumps(tool.input_schema, ensure_ascii=False)


def test_case_event_accepts_telegram_source() -> None:
    event = CaseAddEventInput(
        case_id="c1",
        source="telegram",
        kind="message",
        source_ref=GROUP_MESSAGE.message_id,
        url=GROUP_MESSAGE.link,
        summary="Борис прислал договор",
    )

    assert event.source == "telegram"


def test_no_secrets_file_means_no_telegram(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO)

    assert build_telegram_source(None, TIMEZONE, ASSISTANT_BOT_CREDENTIAL) is None
    assert (
        build_telegram_source(
            str(tmp_path / "telegram_user"), TIMEZONE, ASSISTANT_BOT_CREDENTIAL
        )
        is None
    )
    assert "Telegram tools are off" in caplog.text


def test_secrets_file_builds_source_without_connecting(tmp_path: Path) -> None:
    secrets = tmp_path / "telegram_user"
    secrets.write_text(
        "session=1BVtsOK8Bu0aZ-synthetic-session==\napi_id=123456\n"
        "api_hash=0123456789abcdef0123456789abcdef\n",
        encoding="utf-8",
    )

    source = build_telegram_source(str(secrets), TIMEZONE, ASSISTANT_BOT_CREDENTIAL)

    assert source is not None
    assert [tool.name for tool in build_telegram_tools(source, TIMEZONE)] == list(
        TELEGRAM_TOOL_NAMES
    )


def test_bot_conversation_id_is_token_prefix() -> None:
    assert bot_conversation_id(ASSISTANT_BOT_CREDENTIAL) == "7001"


def test_prompt_without_telegram_drops_its_section() -> None:
    prompt = _prompt(("todoist", "gmail", "whatsapp"))

    for absent in (*TELEGRAM_TOOL_NAMES, "source=telegram", "<!--"):
        assert absent not in prompt


def test_prompt_with_telegram_has_section_and_file_line() -> None:
    prompt = _prompt(("telegram",))

    assert "## Переписка Telegram" in prompt
    assert "file_take, source=telegram" in prompt
    for name in TELEGRAM_TOOL_NAMES:
        assert name in prompt
    assert "search_whatsapp" not in prompt
    assert "<!--" not in prompt
