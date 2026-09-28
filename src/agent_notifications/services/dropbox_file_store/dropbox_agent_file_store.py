import os
from pathlib import Path, PurePosixPath

from src.agent_notifications.models.human_size import human_size
from src.agent_notifications.services.dropbox_file_store.protocols.i_dropbox_file_reader import (
    IDropboxFileReader,
)

AGENTS_FOLDER = ("Personal Assistant", "agents")


class DropboxAgentFileStore:
    def __init__(self, dropbox: IDropboxFileReader, size_limit_bytes: int) -> None:
        self._dropbox = dropbox
        self._size_limit_bytes = size_limit_bytes

    def refusal(self, path: str) -> str | None:
        parts = PurePosixPath(path.lstrip("/")).parts
        if ".." in parts:
            return "путь содержит «..»"
        if len(parts) <= len(AGENTS_FOLDER) or parts[: len(AGENTS_FOLDER)] != (
            AGENTS_FOLDER
        ):
            return "путь вне Personal Assistant/agents/"
        entry = self._entry(path)
        if entry.resolve() != entry:
            return "путь идёт через symlink"
        if not os.path.lexists(entry):
            return None
        if not entry.is_file():
            return "по пути не файл"
        size = entry.stat().st_size
        if size > self._size_limit_bytes:
            return (
                f"файл {human_size(size)} больше предела "
                f"{human_size(self._size_limit_bytes)}"
            )
        return None

    def read(self, path: str) -> bytes | None:
        if not os.path.lexists(self._entry(path)):
            return None
        with self._dropbox.open_read(path.lstrip("/")) as file:
            return file.read()

    def _entry(self, path: str) -> Path:
        return self._dropbox.root.joinpath(*PurePosixPath(path.lstrip("/")).parts)
