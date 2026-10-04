import asyncio
import logging
import os
import shlex
import shutil
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from src.knowledge_intake.errors.intake_git_error import IntakeGitError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _GitOutcome:
    returncode: int
    stdout: str
    stderr: str


class GitCli:
    def __init__(
        self,
        repo_dir: Path,
        ssh_key_path: Path | None = None,
        timeout_seconds: float = 120.0,
    ) -> None:
        self._repo_dir = repo_dir
        self._ssh_key_path = ssh_key_path
        self._timeout_seconds = timeout_seconds
        self._last_error = ""

    @property
    def last_error(self) -> str:
        return self._last_error

    def run_checked(self, *args: str, cwd: Path | None = None) -> str:
        outcome = self._run_blocking(args, cwd or self._repo_dir)
        if outcome.returncode != 0:
            raise IntakeGitError(_command_name(args), outcome.stderr.strip())
        return outcome.stdout

    def succeeds(self, *args: str, cwd: Path | None = None) -> bool:
        outcome = self._run_blocking(args, cwd or self._repo_dir)
        if outcome.returncode != 0:
            self._last_error = outcome.stderr.strip()
            logger.warning("git %s failed: %s", _command_name(args), self._last_error)
        return outcome.returncode == 0

    # Прогон может идти после модели, чей провайдер держит свой event loop: git — своим циклом в потоке
    def _run_blocking(self, args: tuple[str, ...], cwd: Path) -> _GitOutcome:
        with ThreadPoolExecutor(max_workers=1) as executor:
            return executor.submit(asyncio.run, self._run(args, cwd)).result()

    async def _run(self, args: tuple[str, ...], cwd: Path) -> _GitOutcome:
        process = await asyncio.create_subprocess_exec(
            self._git_executable(),
            *args,
            cwd=cwd,
            env=self._environment(),
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(
            process.communicate(), timeout=self._timeout_seconds
        )
        return _GitOutcome(
            returncode=process.returncode if process.returncode is not None else -1,
            stdout=stdout.decode("utf-8", errors="replace"),
            stderr=stderr.decode("utf-8", errors="replace"),
        )

    def _git_executable(self) -> str:
        executable = shutil.which("git")
        if executable is None:
            raise IntakeGitError("which", "git не найден в PATH")
        return executable

    def _environment(self) -> dict[str, str]:
        environment = dict(os.environ)
        environment["GIT_TERMINAL_PROMPT"] = "0"
        if self._ssh_key_path is not None:
            environment["GIT_SSH_COMMAND"] = (
                f"ssh -i {shlex.quote(str(self._ssh_key_path))}"
                " -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new"
            )
        return environment


def _command_name(args: tuple[str, ...]) -> str:
    return next((arg for arg in args if not arg.startswith("-") and "=" not in arg), "")
