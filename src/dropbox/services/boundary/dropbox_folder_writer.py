import unicodedata
from pathlib import PurePosixPath

from src.dropbox.services.boundary.dropbox_access_denied_error import (
    DropboxAccessDeniedError,
)
from src.dropbox.services.boundary.protocols.i_dropbox_new_file_boundary import (
    IDropboxNewFileBoundary,
)


class DropboxFolderWriter:
    def __init__(self, boundary: IDropboxNewFileBoundary, folder: str) -> None:
        folder_parts = _parts(folder)
        if not folder_parts or ".." in folder_parts:
            raise ValueError(f"«{folder}» — не папка внутри Dropbox")
        self._boundary = boundary
        self._folder_parts = folder_parts

    @property
    def folder(self) -> str:
        return "/".join(self._folder_parts)

    def write_new_file(self, path: str, content: bytes) -> str:
        parts = self._parts_inside_folder(path)
        parent = "/".join(parts[:-1])
        resolved_parent = self._boundary.resolve(parent)
        if not resolved_parent.is_relative_to(self._boundary.resolve(self.folder)):
            raise DropboxAccessDeniedError(
                f"{path} ведёт за пределы папки «{self.folder}» — писать можно только в неё"
            )
        return self._boundary.write_new_file(parent, parts[-1], content)

    def _parts_inside_folder(self, path: str) -> tuple[str, ...]:
        if PurePosixPath(path.strip()).is_absolute():
            raise DropboxAccessDeniedError(
                f"{path} — абсолютный путь; нужен путь от корня хранилища, "
                f"начинающийся с «{self.folder}/»"
            )
        parts = _parts(path)
        if ".." in parts:
            raise DropboxAccessDeniedError(
                f"Путь {path} содержит «..» — так выходить нельзя"
            )
        prefix = len(self._folder_parts)
        if len(parts) <= prefix or parts[:prefix] != self._folder_parts:
            raise DropboxAccessDeniedError(
                f"{path} лежит вне папки «{self.folder}» — писать можно только в неё"
            )
        return parts


def _parts(path: str) -> tuple[str, ...]:
    normalized = unicodedata.normalize("NFC", path.strip())
    return tuple(
        part for part in PurePosixPath(normalized).parts if part not in ("", ".", "/")
    )
