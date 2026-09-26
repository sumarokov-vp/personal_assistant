import os
import stat
from pathlib import Path, PurePosixPath
from typing import BinaryIO

from src.dropbox.services.boundary.dropbox_access_denied_error import (
    DropboxAccessDeniedError,
)
from src.dropbox.services.boundary.dropbox_access_policy import DropboxAccessPolicy
from src.dropbox.services.boundary.dropbox_move_refused_error import (
    DropboxMoveRefusedError,
)
from src.dropbox.services.boundary.opened_file_path import opened_file_path

NEW_FILE_MODE = 0o644


class DropboxBoundary:
    def __init__(self, root: Path, policy: DropboxAccessPolicy) -> None:
        self._root = root.resolve()
        self._policy = policy

    @property
    def root(self) -> Path:
        return self._root

    def resolve(self, path: str) -> Path:
        requested, denial = self._requested_parts(path)
        if denial is not None:
            raise DropboxAccessDeniedError(denial)
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

    def write_new_file(self, folder: str, name: str, content: bytes) -> str:
        name_denial = self._file_name_denial(name)
        if name_denial is not None:
            raise DropboxAccessDeniedError(name_denial)
        directory = self.resolve(folder)
        if directory.exists() and not directory.is_dir():
            raise NotADirectoryError(f"{folder} — файл, а не папка")
        target = self._free_name(directory, name)
        if self._policy.is_hidden(target.relative_to(self._root).parts):
            raise DropboxAccessDeniedError(
                f"{self.relative(target)} — закрытая часть Dropbox, доступа нет"
            )
        directory.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(
            target,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            NEW_FILE_MODE,
        )
        with os.fdopen(descriptor, "wb") as file:
            file.write(content)
        return self.relative(target)

    def move_denial(self, source: str, target: str) -> str | None:
        source_entry, denial = self._entry(source)
        if source_entry is None:
            return denial
        target_entry, denial = self._entry(target)
        if target_entry is None:
            return denial
        return self._source_denial(source, source_entry) or self._target_denial(
            source_entry, target, target_entry
        )

    def move(self, source: str, target: str) -> str:
        denial = self.move_denial(source, target)
        source_entry, _ = self._entry(source)
        target_entry, _ = self._entry(target)
        if denial is not None or source_entry is None or target_entry is None:
            raise DropboxMoveRefusedError(denial)
        target_entry.parent.mkdir(parents=True, exist_ok=True)
        os.rename(source_entry, target_entry)
        return self.relative(target_entry)

    def _source_denial(self, source: str, entry: Path) -> str | None:
        if not os.path.lexists(entry):
            return f"В Dropbox нет {source}"
        if entry.is_symlink():
            return f"{source} — ссылка, ссылки не переносятся"
        if self._policy.is_key_file(entry.name):
            return f"{source} — ключевой файл, он не переносится"
        if self._policy.is_immovable(entry.relative_to(self._root).parts):
            return f"{source} лежит в Apps/ — туда пишут приложения, не переносится"
        if entry.is_dir():
            closed = self._closed_entry_inside(entry)
            if closed is not None:
                return (
                    f"В папке {source} есть {closed} — закрытое или ключевое, "
                    "папку целиком не переносим"
                )
        return None

    def _target_denial(
        self, source_entry: Path, target: str, entry: Path
    ) -> str | None:
        if self._policy.is_immovable(entry.relative_to(self._root).parts):
            return f"{target} — в Apps/ ничего не переносится"
        if os.path.lexists(entry):
            return f"{target} уже занят — перезаписи нет"
        if entry.is_relative_to(source_entry):
            return f"Папку нельзя перенести внутрь неё самой: {target}"
        parent = entry.parent
        while not os.path.lexists(parent):
            parent = parent.parent
        if not parent.is_dir():
            return f"{self.relative(parent)} — файл, в него нельзя положить {target}"
        return None

    def _closed_entry_inside(self, directory: Path) -> str | None:
        for current, folders, files in os.walk(directory):
            for name in [*folders, *files]:
                entry = Path(current) / name
                relative = entry.relative_to(self._root)
                if self._policy.is_hidden(relative.parts) or self._policy.is_key_file(
                    name
                ):
                    return relative.as_posix()
        return None

    def _entry(self, path: str) -> tuple[Path | None, str | None]:
        requested, denial = self._requested_parts(path)
        if denial is not None:
            return None, denial
        if not requested:
            return None, "Корень Dropbox не переносится"
        parent = self._root.joinpath(*requested[:-1]).resolve()
        entry = parent / requested[-1]
        if not self._is_visible_path(entry):
            return None, f"{path} — закрытая часть Dropbox, доступа нет"
        return entry, None

    def _free_name(self, directory: Path, name: str) -> Path:
        candidate = directory / name
        pure = PurePosixPath(name)
        copy_number = 2
        while os.path.lexists(candidate):
            candidate = directory / f"{pure.stem} ({copy_number}){pure.suffix}"
            copy_number += 1
        return candidate

    def _file_name_denial(self, name: str) -> str | None:
        if name in ("", ".", "..") or "/" in name or "\\" in name:
            return f"«{name}» — не имя файла"
        if name.startswith("."):
            return f"«{name}» — скрытые файлы не сохраняются"
        return None

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

    def _requested_parts(self, path: str) -> tuple[tuple[str, ...], str | None]:
        candidate = Path(path.strip())
        if candidate.is_absolute():
            if not candidate.is_relative_to(self._root):
                return (), f"{path} лежит вне Dropbox"
            candidate = candidate.relative_to(self._root)
        requested = tuple(part for part in candidate.parts if part not in ("", "."))
        if ".." in requested:
            return (), f"Путь {path} содержит «..» — так выходить нельзя"
        if self._policy.is_hidden(requested):
            return (), f"{path} — закрытая часть Dropbox, доступа нет"
        return requested, None

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
