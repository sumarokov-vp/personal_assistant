import asyncio
import shutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


class GitHeadReader:
    def __init__(self, timeout_seconds: float = 10.0) -> None:
        self._timeout_seconds = timeout_seconds

    def head_of(self, directory: Path) -> str | None:
        git = shutil.which("git")
        if git is None or not directory.is_dir():
            return None
        root = directory.resolve()
        # Каталог читается и изнутри event loop провайдера (инструменты модели): asyncio.run в
        # том же потоке там падает, поэтому git идёт своим циклом в отдельном потоке.
        with ThreadPoolExecutor(max_workers=1) as executor:
            return executor.submit(asyncio.run, self._head(git, root)).result()

    async def _head(self, git: str, root: Path) -> str | None:
        # Клон смонтирован в контейнер с чужим владельцем: без safe.directory git откажется
        # его читать, и версия молча станет sha256 файла.
        process = await asyncio.create_subprocess_exec(
            git,
            "-c",
            f"safe.directory={root}",
            "-C",
            str(root),
            "rev-parse",
            "--show-toplevel",
            "HEAD",
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(
            process.communicate(), timeout=self._timeout_seconds
        )
        if process.returncode != 0:
            return None
        lines = stdout.decode("utf-8", errors="replace").splitlines()
        if len(lines) != 2 or Path(lines[0]).resolve() != root:
            return None
        return lines[1].strip()
