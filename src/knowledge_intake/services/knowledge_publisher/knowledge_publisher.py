from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from src.knowledge_intake.models.accepted_letter import AcceptedLetter
from src.knowledge_intake.models.knowledge_entry import KnowledgeEntry
from src.knowledge_intake.services.entities.push_outcome import PushOutcome
from src.knowledge_intake.services.knowledge_publisher.protocols.i_git import IGit
from src.knowledge_intake.services.knowledge_publisher.protocols.i_knowledge_files import (
    IKnowledgeFiles,
)

# Откат знания: git revert <sha> и снова подъём patch-версии плагина — без него откат
# до сотрудников не доедет (claude-toolkit/CLAUDE.md, правило версии)


class KnowledgePublisher:
    def __init__(
        self,
        git: IGit,
        files: IKnowledgeFiles,
        clone_dir: Path,
        remote_url: str,
        branch: str,
        author_name: str,
        author_email: str,
        timezone: ZoneInfo,
    ) -> None:
        self._git = git
        self._files = files
        self._clone_dir = clone_dir
        self._remote_url = remote_url
        self._branch = branch
        self._identity = (
            "-c",
            f"user.name={author_name}",
            "-c",
            f"user.email={author_email}",
            "-c",
            "commit.gpgsign=false",
        )
        self._timezone = timezone
        self._touched_plugins: list[str] = []
        self._knowledge_commits = 0

    def prepare(self) -> None:
        self._touched_plugins = []
        self._knowledge_commits = 0
        if not (self._clone_dir / ".git").exists():
            self._clone_dir.mkdir(parents=True, exist_ok=True)
            self._git.run_checked(
                "clone",
                "--branch",
                self._branch,
                self._remote_url,
                str(self._clone_dir),
                cwd=self._clone_dir.parent,
            )
            return
        self._git.run_checked("fetch", "origin", self._branch)
        self._reset_to_remote()

    def publish(self, entry: KnowledgeEntry, letter: AcceptedLetter) -> None:
        today = datetime.now(tz=self._timezone).date()
        self._files.write(entry, letter.sender, today)
        self._git.run_checked(
            "add", "--all", "--", str(self._files.plugin_path(entry.plugin))
        )
        self._git.run_checked(
            *self._identity,
            "commit",
            "-m",
            f"knowledge({entry.plugin}): {_one_line(entry.topic)}",
            "-m",
            f"Письмо: {_one_line(letter.subject)}\nMessage-ID: {letter.message_id}",
            "-m",
            f"Suggested-by: {letter.sender.signature()}",
        )
        self._knowledge_commits += 1
        if entry.plugin not in self._touched_plugins:
            self._touched_plugins.append(entry.plugin)

    def finish(self) -> PushOutcome:
        if not self._knowledge_commits:
            return PushOutcome(pushed=True)
        versions = {
            plugin: self._files.bump_patch_version(plugin)
            for plugin in self._touched_plugins
        }
        for plugin in versions:
            self._git.run_checked("add", "--", str(self._files.plugin_path(plugin)))
        self._git.run_checked(
            *self._identity,
            "commit",
            "-m",
            "chore("
            + ", ".join(versions)
            + "): версия после знаний — "
            + ", ".join(f"{plugin} {version}" for plugin, version in versions.items()),
        )
        if not self._push_with_one_retry():
            error = self._git.last_error
            self._reset_to_remote()
            return PushOutcome(pushed=False, versions=versions, error=error)
        shas = self._git.run_checked(
            "rev-list",
            "--reverse",
            f"--max-count={self._knowledge_commits + 1}",
            "HEAD",
        ).split()
        return PushOutcome(pushed=True, commit_shas=shas[:-1], versions=versions)

    def _push_with_one_retry(self) -> bool:
        if self._git.succeeds("push", "origin", f"HEAD:{self._branch}"):
            return True
        if not self._git.succeeds("pull", "--rebase", "origin", self._branch):
            return False
        return self._git.succeeds("push", "origin", f"HEAD:{self._branch}")

    def _reset_to_remote(self) -> None:
        git_dir = self._clone_dir / ".git"
        if (git_dir / "rebase-merge").exists() or (git_dir / "rebase-apply").exists():
            self._git.run_checked("rebase", "--abort")
        self._git.run_checked("reset", "--hard", f"origin/{self._branch}")
        self._git.run_checked("clean", "-fd")


def _one_line(text: str) -> str:
    return " ".join(text.split())
