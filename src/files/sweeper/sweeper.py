import os
import time
from collections.abc import Sequence
from datetime import timedelta
from pathlib import Path

DEFAULT_MAX_AGE = timedelta(hours=24)


class Sweeper:
    def __init__(
        self, roots: Sequence[Path], max_age: timedelta = DEFAULT_MAX_AGE
    ) -> None:
        self._roots = list(roots)
        self._max_age = max_age

    def sweep(self) -> list[Path]:
        deadline = time.time() - self._max_age.total_seconds()
        removed: list[Path] = []
        for root in self._roots:
            if root.is_dir() and not root.is_symlink():
                self._sweep_directory(root, deadline, removed)
        return removed

    def _sweep_directory(
        self, directory: Path, deadline: float, removed: list[Path]
    ) -> None:
        with os.scandir(directory) as entries:
            children = list(entries)
        for entry in children:
            path = Path(entry.path)
            if entry.is_symlink():
                continue
            if entry.is_dir(follow_symlinks=False):
                self._sweep_subdirectory(path, deadline, removed)
            elif entry.stat(follow_symlinks=False).st_mtime < deadline:
                path.unlink(missing_ok=True)
                removed.append(path)

    def _sweep_subdirectory(
        self, directory: Path, deadline: float, removed: list[Path]
    ) -> None:
        was_stale = directory.lstat().st_mtime < deadline
        removed_before = len(removed)
        self._sweep_directory(directory, deadline, removed)
        emptied_now = len(removed) > removed_before
        if (was_stale or emptied_now) and not any(directory.iterdir()):
            directory.rmdir()
            removed.append(directory)
