from dataclasses import dataclass
from pathlib import Path

import pytest

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
class WikiRemote:
    bare_dir: Path
    url: str
    owner_dir: Path

    def bare_git(self) -> GitCli:
        return GitCli(self.bare_dir)

    def owner_commit(self, relative_path: str, content: str, message: str) -> str:
        owner_git = GitCli(self.owner_dir)
        owner_git.run_checked("pull", "--rebase", "origin", "main")
        file = self.owner_dir / relative_path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(content, encoding="utf-8")
        owner_git.run_checked("add", "--", relative_path)
        owner_git.run_checked(*OWNER_IDENTITY, "commit", "-m", message)
        owner_git.run_checked("push", "origin", "HEAD:main")
        return owner_git.run_checked("rev-parse", "HEAD").strip()

    def owner_symlink(self, relative_path: str, target: Path) -> None:
        owner_git = GitCli(self.owner_dir)
        link = self.owner_dir / relative_path
        link.parent.mkdir(parents=True, exist_ok=True)
        link.symlink_to(target)
        owner_git.run_checked("add", "--", relative_path)
        owner_git.run_checked(*OWNER_IDENTITY, "commit", "-m", "symlink")
        owner_git.run_checked("push", "origin", "HEAD:main")

    def main_head(self) -> str:
        return self.bare_git().run_checked("rev-parse", "main").strip()

    def main_file(self, relative_path: str) -> str:
        return self.bare_git().run_checked("show", f"main:{relative_path}")


@pytest.fixture
def wiki_remote(tmp_path: Path) -> WikiRemote:
    bare_dir = tmp_path / "remote.git"
    bare_dir.mkdir()
    GitCli(bare_dir).run_checked("init", "--bare", "--initial-branch=main")
    url = bare_dir.as_uri()
    owner_dir = tmp_path / "owner"
    GitCli(tmp_path).run_checked("clone", url, str(owner_dir))
    owner_git = GitCli(owner_dir)
    owner_git.run_checked("checkout", "-B", "main")
    (owner_dir / "Wiki").mkdir()
    (owner_dir / "Wiki" / "Existing.md").write_text(
        "# Existing\n\nfirst line\n", encoding="utf-8"
    )
    (owner_dir / ".obsidian").mkdir()
    (owner_dir / ".obsidian" / "app.json").write_text("{}\n", encoding="utf-8")
    owner_git.run_checked("add", "-A")
    owner_git.run_checked(*OWNER_IDENTITY, "commit", "-m", "initial")
    owner_git.run_checked("push", "origin", "HEAD:main")
    return WikiRemote(bare_dir=bare_dir, url=url, owner_dir=owner_dir)
