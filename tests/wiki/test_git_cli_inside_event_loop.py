import asyncio
from pathlib import Path

from src.wiki.repos.git_cli import GitCli


def test_git_runs_from_tool_called_inside_running_event_loop(tmp_path: Path) -> None:
    async def tool_call_from_provider_loop() -> str:
        git = GitCli(tmp_path)
        git.run_checked("init", "--initial-branch=main")
        return git.run_checked("rev-parse", "--git-dir").strip()

    assert asyncio.run(tool_call_from_provider_loop()) == ".git"
