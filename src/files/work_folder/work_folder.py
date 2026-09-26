import os
import re
import secrets
from pathlib import Path

from src.files.work_folder.work_file import WorkFile
from src.files.work_folder.work_file_not_found_error import WorkFileNotFoundError

METADATA_NAME = ".work_file.json"
FALLBACK_NAME = "file"
FILE_ID_BYTES = 4
FILE_ID_PATTERN = re.compile(r"[0-9a-f]{8}")
PRIVATE_DIR_MODE = 0o700
PRIVATE_FILE_MODE = 0o600
UNSAFE_NAME_CHARACTERS = re.compile(r"[\x00-\x1f\x7f]")


class WorkFolder:
    def __init__(self, root: Path) -> None:
        self._root = root

    @property
    def root(self) -> Path:
        return self._root

    def put(self, content: bytes, name: str, media_type: str, source: str) -> WorkFile:
        self._root.mkdir(mode=PRIVATE_DIR_MODE, parents=True, exist_ok=True)
        file_id, directory = self._new_directory()
        work_file = WorkFile(
            id=file_id,
            name=_safe_name(name),
            media_type=media_type,
            size=len(content),
            source=source,
        )
        _write_new(directory / work_file.name, content)
        _write_new(directory / METADATA_NAME, work_file.model_dump_json().encode())
        return work_file

    def get(self, file_id: str) -> WorkFile:
        metadata = self._directory(file_id) / METADATA_NAME
        if not metadata.is_file():
            raise WorkFileNotFoundError(f"Файла {file_id} нет в рабочей папке")
        return WorkFile.model_validate_json(metadata.read_bytes())

    def read(self, file_id: str) -> bytes:
        work_file = self.get(file_id)
        content = self._directory(file_id) / work_file.name
        if not content.is_file():
            raise WorkFileNotFoundError(f"Файла {file_id} нет в рабочей папке")
        return content.read_bytes()

    def _directory(self, file_id: str) -> Path:
        if not FILE_ID_PATTERN.fullmatch(file_id):
            raise WorkFileNotFoundError(f"«{file_id}» — не идентификатор файла")
        return self._root / file_id

    def _new_directory(self) -> tuple[str, Path]:
        file_id = secrets.token_hex(FILE_ID_BYTES)
        while os.path.lexists(self._root / file_id):
            file_id = secrets.token_hex(FILE_ID_BYTES)
        directory = self._root / file_id
        directory.mkdir(mode=PRIVATE_DIR_MODE)
        return file_id, directory


def _safe_name(name: str) -> str:
    last_part = re.split(r"[/\\]", name)[-1]
    cleaned = UNSAFE_NAME_CHARACTERS.sub("", last_part).strip().lstrip(".").strip()
    return cleaned or FALLBACK_NAME


def _write_new(path: Path, content: bytes) -> None:
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, PRIVATE_FILE_MODE
    )
    with os.fdopen(descriptor, "wb") as file:
        file.write(content)
