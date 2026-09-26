from pathlib import Path

from src.wiki.errors.wiki_git_error import WikiGitError
from src.wiki.errors.wiki_page_changed_error import WikiPageChangedError
from src.wiki.services.wiki_sync.protocols.i_git import IGit


class WikiSync:
    def __init__(
        self,
        git: IGit,
        wiki_dir: Path,
        remote_url: str,
        branch: str = "main",
        push_attempts: int = 3,
    ) -> None:
        self._git = git
        self._wiki_dir = wiki_dir
        self._remote_url = remote_url
        self._branch = branch
        self._push_attempts = push_attempts

    def refresh(self) -> None:
        if not (self._wiki_dir / ".git").exists():
            self._clone()
            return
        self._drop_unfinished_work()
        if not self._git.succeeds("pull", "--rebase", "origin", self._branch):
            self._reset_to_remote()
            raise WikiGitError("pull", "не удалось обновить копию вики из origin")

    def publish(self) -> None:
        for _ in range(self._push_attempts):
            if self._git.succeeds("push", "origin", f"HEAD:{self._branch}"):
                return
            if not self._git.succeeds("pull", "--rebase", "origin", self._branch):
                conflicted = self._rebase_in_progress()
                self._reset_to_remote()
                if conflicted:
                    raise WikiPageChangedError()
                raise WikiGitError(
                    "pull", "не удалось подтянуть origin после отказа push"
                )
        self._reset_to_remote()
        raise WikiGitError("push", f"не прошёл за {self._push_attempts} попыток")

    def discard_local_commit(self) -> None:
        self._reset_to_remote()

    def _clone(self) -> None:
        self._wiki_dir.mkdir(parents=True, exist_ok=True)
        self._git.run_checked(
            "clone",
            "--branch",
            self._branch,
            self._remote_url,
            str(self._wiki_dir),
            cwd=self._wiki_dir.parent,
        )

    def _drop_unfinished_work(self) -> None:
        if self._rebase_in_progress():
            self._git.run_checked("rebase", "--abort")
        self._git.run_checked("reset", "--hard", "HEAD")
        self._git.run_checked("clean", "-fd")

    def _reset_to_remote(self) -> None:
        if self._rebase_in_progress():
            self._git.run_checked("rebase", "--abort")
        self._git.run_checked("reset", "--hard", f"origin/{self._branch}")

    def _rebase_in_progress(self) -> bool:
        git_dir = self._wiki_dir / ".git"
        return (git_dir / "rebase-merge").exists() or (
            git_dir / "rebase-apply"
        ).exists()
