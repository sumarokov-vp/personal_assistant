import os
import stat
from pathlib import Path
from typing import BinaryIO

from src.dropbox.services.boundary.dropbox_access_denied_error import (
    DropboxAccessDeniedError,
)
from src.dropbox.services.boundary.dropbox_access_policy import DropboxAccessPolicy
from src.dropbox.services.boundary.opened_file_path import opened_file_path


class DropboxBoundary:
    def __init__(self, root: Path, policy: DropboxAccessPolicy) -> None:
        self._root = root.resolve()
        self._policy = policy

    @property
    def root(self) -> Path:
        return self._root

    def resolve(self, path: str) -> Path:
        requested = self._requested_parts(path)
        if ".." in requested:
            raise DropboxAccessDeniedError(
                f"Путь {path} содержит «..» — так выходить нельзя"
            )
        if self._policy.is_hidden(requested):
            raise DropboxAccessDeniedError(
                f"{path} — закрытая часть Dropbox, доступа нет"
            )
        resolved = self._root.joinpath(*requested).resolve()
        self._ensure_visible(resolved, path)
        return resolved

    def relative(self, path: Path) -> str:
        return path.relative_to(self._root).as_posix()

    def visible_children(self, directory: Path) -> list[Path]:
        self._ensure_visible(directory.resolve(), self.relative(directory))
        return sorted(
            (child for child in directory.iterdir() if self._is_visible_entry(child)),
            key=lambda child: child.name.casefold(),
        )

    def is_key_file(self, path: Path) -> bool:
        return self._policy.is_key_file(path.name)

    def open_read(self, path: str) -> BinaryIO:
        resolved = self.resolve(path)
        if self._policy.is_key_file(resolved.name) or self._policy.is_key_file(
            Path(path).name
        ):
            raise DropboxAccessDeniedError(
                f"{path} — ключевой файл, его содержимое закрыто; видно только имя"
            )
        if resolved.is_dir():
            raise IsADirectoryError(f"{path} — папка, а не файл")
        if not resolved.is_file():
            raise FileNotFoundError(f"В Dropbox нет файла {path}")
        descriptor = os.open(resolved, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        file = os.fdopen(descriptor, "rb")
        self._ensure_opened_regular_file(file, path)
        return file

    def _ensure_opened_regular_file(self, file: BinaryIO, requested: str) -> None:
        descriptor = file.fileno()
        opened = opened_file_path(descriptor)
        if not stat.S_ISREG(os.fstat(descriptor).st_mode) or not self._is_visible_path(
            opened
        ):
            file.close()
            raise DropboxAccessDeniedError(
                f"{requested} подменён во время чтения — отказ"
            )

    def _requested_parts(self, path: str) -> tuple[str, ...]:
        candidate = Path(path.strip())
        if candidate.is_absolute():
            if not candidate.is_relative_to(self._root):
                raise DropboxAccessDeniedError(f"{path} лежит вне Dropbox")
            candidate = candidate.relative_to(self._root)
        return tuple(part for part in candidate.parts if part not in ("", "."))

    def _ensure_visible(self, resolved: Path, requested: str) -> None:
        if not resolved.is_relative_to(self._root):
            raise DropboxAccessDeniedError(f"{requested} ведёт за пределы Dropbox")
        if self._policy.is_hidden(resolved.relative_to(self._root).parts):
            raise DropboxAccessDeniedError(
                f"{requested} — закрытая часть Dropbox, доступа нет"
            )

    def _is_visible_entry(self, entry: Path) -> bool:
        if self._policy.is_hidden(entry.relative_to(self._root).parts):
            return False
        return not entry.is_symlink() or self._is_visible_path(entry.resolve())

    def _is_visible_path(self, path: Path) -> bool:
        return path.is_relative_to(self._root) and not self._policy.is_hidden(
            path.relative_to(self._root).parts
        )
