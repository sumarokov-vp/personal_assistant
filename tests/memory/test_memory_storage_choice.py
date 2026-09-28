import json
from datetime import date
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from ai_framework.entities.tool_context import ToolContext

from src.ai_tools import MemoryShowTool, MemoryUpsertDeadlineTool
from src.ai_tools.memory_show.tool import MemoryShowInput
from src.ai_tools.memory_upsert_deadline.tool import MemoryUpsertDeadlineInput
from src.memory.models import Deadline
from src.memory.repos import (
    DeadlineRepository,
    LocalFolderStorage,
    WikiPageStorage,
)
from src.wiki import WikiFactory, WikiSettings
from workers.bot import __main__ as bot_main
from workers.memory_fill import composition as fill_composition
from workers.memory_fill.memory_fill_env import read_memory_fill_env
from workers.memory_fill.memory_storage_kind import MemoryStorageKind
from workers.memory_fill.memory_storage_settings import (
    DEFAULT_MEMORY_DIR,
    MemoryStorageSettings,
    read_memory_storage_settings,
)

CONTEXT = ToolContext({"chat_id": 1, "user_id": 1})
TIMEZONE = ZoneInfo("Asia/Almaty")
DEADLINES_PAGE = Path("Assistant") / "Реестр сроков.md"


@pytest.fixture
def memory_env(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    for name in ("MEMORY_STORAGE", "MEMORY_DIR", "WIKI_DIR", "WIKI_REMOTE_URL"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("AI_MODEL", "unused")
    monkeypatch.setenv("AI_DB_URL", "postgres://unused")
    return monkeypatch


def test_local_folder_is_default(memory_env: pytest.MonkeyPatch):
    settings = read_memory_storage_settings()

    assert settings == MemoryStorageSettings(
        MemoryStorageKind.LOCAL, DEFAULT_MEMORY_DIR
    )


def test_unknown_storage_kind_fails(memory_env: pytest.MonkeyPatch):
    memory_env.setenv("MEMORY_STORAGE", "obsidian")

    with pytest.raises(ValueError, match="MEMORY_STORAGE"):
        read_memory_storage_settings()


def test_bot_without_wiki_settings_keeps_memory_in_local_folder(
    memory_env: pytest.MonkeyPatch, tmp_path: Path
):
    memory_env.setenv("MEMORY_DIR", str(tmp_path))
    wiki_factory = bot_main.build_configured_wiki_factory()
    storage = bot_main.build_memory_storage(
        read_memory_storage_settings(), wiki_factory
    )
    tools = {tool.name: tool for tool in bot_main.build_memory_tools(storage, TIMEZONE)}

    upsert = tools["memory_upsert_deadline"]
    assert isinstance(upsert, MemoryUpsertDeadlineTool)
    upsert.execute(
        MemoryUpsertDeadlineInput(
            what="Загранпаспорт",
            whose="Владимир",
            expires=date(2030, 1, 1),
            source="диалог",
        ),
        CONTEXT,
    )
    show = tools["memory_show"]
    assert isinstance(show, MemoryShowTool)
    shown = json.loads(show.execute(MemoryShowInput(), CONTEXT))

    assert wiki_factory is None
    assert isinstance(storage, LocalFolderStorage)
    assert "Загранпаспорт" in (tmp_path / DEADLINES_PAGE).read_text(encoding="utf-8")
    pages = {page["page"]: page for page in shown["pages"]}
    [entry] = pages[DEADLINES_PAGE.as_posix()]["entries"]
    assert (entry["what"], entry["expires"]) == ("Загранпаспорт", "01.01.2030")


def test_local_folder_survives_new_storage_instance(tmp_path: Path):
    DeadlineRepository(LocalFolderStorage(tmp_path)).upsert(
        Deadline(
            what="ЭЦП РК", whose="Владимир", expires=date(2027, 3, 1), source="диалог"
        )
    )

    reread = DeadlineRepository(LocalFolderStorage(tmp_path)).read().entries
    assert [entry.what for entry in reread] == ["ЭЦП РК"]
    assert list(tmp_path.rglob(".*")) == []


def test_bot_picks_wiki_storage_on_wiki_switch(
    memory_env: pytest.MonkeyPatch, tmp_path: Path
):
    memory_env.setenv("MEMORY_STORAGE", "wiki")
    memory_env.setenv("WIKI_DIR", str(tmp_path / "wiki"))
    memory_env.setenv("WIKI_REMOTE_URL", "git@example.com:owner/wiki.git")

    wiki_factory = bot_main.build_configured_wiki_factory()
    storage = bot_main.build_memory_storage(
        read_memory_storage_settings(), wiki_factory
    )

    assert isinstance(wiki_factory, WikiFactory)
    assert isinstance(storage, WikiPageStorage)


def test_bot_wiki_switch_without_wiki_dir_fails(memory_env: pytest.MonkeyPatch):
    memory_env.setenv("MEMORY_STORAGE", "wiki")

    with pytest.raises(ValueError, match="WIKI_DIR"):
        bot_main.build_memory_storage(
            read_memory_storage_settings(), bot_main.build_configured_wiki_factory()
        )


def test_memory_fill_follows_the_same_switch(
    memory_env: pytest.MonkeyPatch, tmp_path: Path
):
    memory_env.setenv("MEMORY_DIR", str(tmp_path))
    local = fill_composition.build_memory_storage(read_memory_fill_env())

    memory_env.setenv("MEMORY_STORAGE", "wiki")
    memory_env.setenv("WIKI_REMOTE_URL", "git@example.com:owner/wiki.git")
    wiki_env = read_memory_fill_env()
    wiki = fill_composition.build_memory_storage(wiki_env)

    assert isinstance(local, LocalFolderStorage)
    assert isinstance(wiki, WikiPageStorage)
    assert isinstance(wiki_env.wiki, WikiSettings)
