import json
import threading
from pathlib import Path

import pytest
from ai_framework.entities.tool_context import ToolContext

from src.ai_tools.wiki_read.tool import MAX_CONTENT_CHARS, WikiReadInput, WikiReadTool
from src.ai_tools.wiki_search.tool import WikiSearchInput, WikiSearchTool
from src.wiki.search.wiki_searcher import WikiSearcher
from src.wiki.services.wiki_path_policy.wiki_path_policy import WikiPathPolicy
from src.wiki.services.wiki_reader.wiki_reader import WikiReader


class NoRefresh:
    def refresh(self) -> None:
        pass


@pytest.fixture
def wiki_dir(tmp_path: Path) -> Path:
    pages = {
        "Wiki/Рецепты/Борщ.md": "# Борщ\n\nСвёкла, капуста, говядина.\n",
        "Wiki/Длинная.md": "а" * (MAX_CONTENT_CHARS + 500),
        ".obsidian/app.json": '{"theme": "dark"}',
    }
    for relative_path, content in pages.items():
        file = tmp_path / relative_path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(content, encoding="utf-8")
    return tmp_path


@pytest.fixture
def reader(wiki_dir: Path) -> WikiReader:
    return WikiReader(
        wiki_dir=wiki_dir,
        lock=threading.Lock(),
        refresher=NoRefresh(),
        path_policy=WikiPathPolicy(wiki_dir),
    )


def test_wiki_read_returns_page_text(reader: WikiReader):
    result = json.loads(
        WikiReadTool(reader).execute(
            WikiReadInput(path="Wiki/Рецепты/Борщ.md"), ToolContext()
        )
    )

    assert result["status"] == "ok"
    assert result["path"] == "Wiki/Рецепты/Борщ.md"
    assert "Свёкла" in result["content"]
    assert result["truncated_chars"] == 0


def test_wiki_read_rejects_obsidian_settings(reader: WikiReader):
    result = json.loads(
        WikiReadTool(reader).execute(
            WikiReadInput(path=".obsidian/app.json"), ToolContext()
        )
    )

    assert result["status"] == "error"
    assert "content" not in result
    assert ".obsidian/app.json" in result["message"]


def test_wiki_read_truncates_long_page(reader: WikiReader):
    result = json.loads(
        WikiReadTool(reader).execute(
            WikiReadInput(path="Wiki/Длинная.md"), ToolContext()
        )
    )

    assert result["status"] == "truncated"
    assert len(result["content"]) == MAX_CONTENT_CHARS
    assert result["truncated_chars"] == 500


def test_wiki_search_returns_path_from_root(reader: WikiReader):
    result = json.loads(
        WikiSearchTool(WikiSearcher(reader)).execute(
            WikiSearchInput(query="капуста"), ToolContext()
        )
    )

    assert result["status"] == "found"
    assert [hit["path"] for hit in result["results"]] == ["Wiki/Рецепты/Борщ.md"]
    assert result["results"][0]["title"] == "Борщ"
