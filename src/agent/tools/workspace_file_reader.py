import fcntl
import os
import sys
from pathlib import Path

PATH_BUFFER_SIZE = 1024


class WorkspaceFileReader:
    def __init__(self, workspace_dir: Path) -> None:
        self._workspace_dir = workspace_dir.resolve()

    def read(self, file_path: str) -> bytes:
        resolved = (self._workspace_dir / file_path).resolve()
        self._ensure_inside_workspace(resolved, file_path)
        if not resolved.is_file():
            raise FileNotFoundError(f"File not found in workspace: {file_path}")

        descriptor = os.open(resolved, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(descriptor, "rb") as file:
            self._ensure_inside_workspace(_opened_file_path(file.fileno()), file_path)
            return file.read()

    def _ensure_inside_workspace(self, path: Path, requested: str) -> None:
        if not path.is_relative_to(self._workspace_dir):
            raise PermissionError(
                f"Отправлять можно только файлы из рабочей папки {self._workspace_dir}, "
                f"а {requested} находится вне неё. Скопируй файл в рабочую папку и отправь копию."
            )


def _opened_file_path(descriptor: int) -> Path:
    if sys.platform == "darwin":
        raw = fcntl.fcntl(descriptor, fcntl.F_GETPATH, bytes(PATH_BUFFER_SIZE))
        return Path(os.fsdecode(raw.split(b"\0", 1)[0]))
    return Path(os.readlink(f"/proc/self/fd/{descriptor}"))
