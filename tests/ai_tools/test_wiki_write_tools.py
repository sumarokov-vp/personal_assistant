import json
from dataclasses import dataclass
from pathlib import Path

import pytest
from ai_framework.entities.tool_context import ToolContext

from src.ai_tools.wiki_append.tool import WikiAppendInput, WikiAppendTool
from src.ai_tools.wiki_create_page.tool import (
    WikiCreatePageInput,
    WikiCreatePageTool,
)
from src.wiki import WikiFactory, WikiSettings
from src.wiki.repos.git_cli import GitCli

OWNER_IDENTITY = (
    "-c",
    "user.name=Owner",
    "-c",
    "user.email=owner@example.com",
    "-c",
    "commit.gpgsign=false",
)


@dataclass(frozen=True)
class BareWiki:
    git: GitCli

    def main_file(self, relative_path: str) -> str:
        return self.git.run_checked("show", f"main:{relative_path}")

    def main_head(self) -> str:
        return self.git.run_checked("rev-parse", "main").strip()

    def main_subjects(self) -> list[str]:
        return self.git.run_checked("log", "--format=%s", "main").splitlines()


@dataclass(frozen=True)
class WikiTools:
    create_page: WikiCreatePageTool
    append: WikiAppendTool
    bare: BareWiki


@pytest.fixture
def wiki_tools(tmp_path: Path) -> WikiTools:
    bare_dir = tmp_path / "remote.git"
    bare_dir.mkdir()
    GitCli(bare_dir).run_checked("init", "--bare", "--initial-branch=main")
    owner_dir = tmp_path / "owner"
    GitCli(tmp_path).run_checked("clone", bare_dir.as_uri(), str(owner_dir))
    owner_git = GitCli(owner_dir)
    owner_git.run_checked("checkout", "-B", "main")
    (owner_dir / "Wiki").mkdir()
    (owner_dir / "Wiki" / "Existing.md").write_text("# Existing\n", encoding="utf-8")
    owner_git.run_checked("add", "-A")
    owner_git.run_checked(*OWNER_IDENTITY, "commit", "-m", "initial")
    owner_git.run_checked("push", "origin", "HEAD:main")

    factory = WikiFactory(
        WikiSettings(wiki_dir=tmp_path / "bot" / "wiki", remote_url=bare_dir.as_uri())
    )
    reader = factory.create_reader()
    writer = factory.create_writer()
    return WikiTools(
        create_page=WikiCreatePageTool(creator=writer, lister=reader),
        append=WikiAppendTool(appender=writer),
        bare=BareWiki(GitCli(bare_dir)),
    )


def _create(tools: WikiTools, title: str, content: str, folder: str = "Wiki") -> dict:
    answer = tools.create_page.execute(
        WikiCreatePageInput(title=title, content=content, folder=folder),
        ToolContext(),
    )
    return json.loads(answer)


def test_created_and_appended_page_lands_in_main_with_pa_commits(
    wiki_tools: WikiTools,
):
    created = _create(wiki_tools, "Идея: бот?", "# Идея\n\nпервая мысль")
    appended = json.loads(
        wiki_tools.append.execute(
            WikiAppendInput(path=created["path"], content="вторая мысль"),
            ToolContext(),
        )
    )

    assert created == {"path": "Wiki/Идея бот.md"}
    assert appended == {"path": "Wiki/Идея бот.md"}
    assert wiki_tools.bare.main_file("Wiki/Идея бот.md") == (
        "# Идея\n\nпервая мысль\n\nвторая мысль\n"
    )
    assert wiki_tools.bare.main_subjects()[:2] == [
        "pa: дополнена Wiki/Идея бот.md",
        "pa: создана Wiki/Идея бот.md",
    ]


def test_repeated_create_is_error_and_leaves_page_untouched(wiki_tools: WikiTools):
    _create(wiki_tools, "Заметка", "# Заметка\n\nоригинал")
    head_before = wiki_tools.bare.main_head()

    repeated = _create(wiki_tools, "Заметка", "# Заметка\n\nперезапись")

    assert "error" in repeated
    assert wiki_tools.bare.main_head() == head_before
    assert wiki_tools.bare.main_file("Wiki/Заметка.md") == "# Заметка\n\nоригинал\n"


def test_create_in_missing_folder_is_error_without_commit(wiki_tools: WikiTools):
    head_before = wiki_tools.bare.main_head()

    answer = _create(wiki_tools, "Заметка", "текст", folder="Новая")

    assert "error" in answer
    assert wiki_tools.bare.main_head() == head_before


def test_append_to_missing_page_is_error(wiki_tools: WikiTools):
    answer = json.loads(
        wiki_tools.append.execute(
            WikiAppendInput(path="Wiki/Нет такой.md", content="текст"),
            ToolContext(),
        )
    )

    assert "error" in answer
