import json
import logging
from dataclasses import dataclass
from pathlib import Path

import pytest
from ai_framework.entities.tool_context import ToolContext

from src.ai_tools.wiki_append.tool import WikiAppendInput, WikiAppendTool
from src.ai_tools.wiki_create_page.tool import WikiCreatePageInput, WikiCreatePageTool
from src.ai_tools.wiki_read.tool import WikiReadInput, WikiReadTool
from src.ai_tools.wiki_search.tool import WikiSearchInput, WikiSearchTool
from src.wiki import WikiFactory, WikiSettings
from src.wiki.repos.git_cli import GitCli
from src.wiki.search.wiki_searcher import WikiSearcher
from tests.wiki.conftest import OWNER_IDENTITY, WikiRemote

CP1251_PAGE = "Wiki/1753002353-DBAX.md"
CP1251_BYTES = "# Заметка\n\nсохранена в Windows-1251\n".encode("cp1251")


@dataclass(frozen=True)
class WikiTools:
    search: WikiSearchTool
    read: WikiReadTool
    create_page: WikiCreatePageTool
    append: WikiAppendTool


@pytest.fixture
def tools(tmp_path: Path, wiki_remote: WikiRemote) -> WikiTools:
    owner_git = GitCli(wiki_remote.owner_dir)
    (wiki_remote.owner_dir / CP1251_PAGE).write_bytes(CP1251_BYTES)
    owner_git.run_checked("add", "--", CP1251_PAGE)
    owner_git.run_checked(*OWNER_IDENTITY, "commit", "-m", "cp1251")
    owner_git.run_checked("push", "origin", "HEAD:main")
    factory = WikiFactory(
        WikiSettings(wiki_dir=tmp_path / "bot" / "wiki", remote_url=wiki_remote.url)
    )
    reader = factory.create_reader()
    writer = factory.create_writer()
    return WikiTools(
        search=WikiSearchTool(searcher=WikiSearcher(pages=reader)),
        read=WikiReadTool(reader=reader),
        create_page=WikiCreatePageTool(creator=writer, lister=reader),
        append=WikiAppendTool(appender=writer),
    )


def _answer(raw: str) -> dict[str, object]:
    answer: dict[str, object] = json.loads(raw)
    return answer


def test_create_page_survives_cp1251_page(
    tools: WikiTools, wiki_remote: WikiRemote, caplog: pytest.LogCaptureFixture
):
    with caplog.at_level(logging.WARNING):
        answer = _answer(
            tools.create_page.execute(
                WikiCreatePageInput(title="Голосовая", content="# Голосовая"),
                ToolContext(),
            )
        )

    assert answer == {"path": "Wiki/Голосовая.md"}
    assert wiki_remote.main_file("Wiki/Голосовая.md") == "# Голосовая\n"
    assert CP1251_PAGE in caplog.text


def test_search_and_read_of_other_pages_survive_cp1251_page(
    tools: WikiTools, caplog: pytest.LogCaptureFixture
):
    with caplog.at_level(logging.WARNING):
        found = _answer(
            tools.search.execute(WikiSearchInput(query="first"), ToolContext())
        )
        read = _answer(
            tools.read.execute(WikiReadInput(path="Wiki/Existing.md"), ToolContext())
        )

    assert "error" not in found
    assert "Wiki/Existing.md" in json.dumps(found, ensure_ascii=False)
    assert "first line" in json.dumps(read, ensure_ascii=False)
    assert CP1251_PAGE in caplog.text


def test_read_of_cp1251_page_replaces_undecodable_bytes(tools: WikiTools):
    read = _answer(tools.read.execute(WikiReadInput(path=CP1251_PAGE), ToolContext()))

    assert "error" not in read
    assert "�" in json.dumps(read, ensure_ascii=False)


def test_append_to_cp1251_page_is_refused_without_touching_bytes(
    tools: WikiTools, wiki_remote: WikiRemote
):
    head_before = wiki_remote.main_head()

    answer = _answer(
        tools.append.execute(
            WikiAppendInput(path=CP1251_PAGE, content="дописка"), ToolContext()
        )
    )

    assert "UTF-8" in str(answer["error"])
    assert wiki_remote.main_head() == head_before
    blob = wiki_remote.bare_git().run_checked("rev-parse", f"main:{CP1251_PAGE}")
    assert blob.strip() == _blob_sha(CP1251_BYTES, wiki_remote)


def _blob_sha(content: bytes, wiki_remote: WikiRemote) -> str:
    probe = wiki_remote.owner_dir.parent / "probe.bin"
    probe.write_bytes(content)
    return GitCli(wiki_remote.owner_dir).run_checked("hash-object", str(probe)).strip()
