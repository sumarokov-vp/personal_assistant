from pathlib import Path

import yaml
from pydantic import TypeAdapter

from src.colleague_mail.models.colleague import Colleague
from src.colleague_mail.repos.colleague_directory_entry import (
    ColleagueDirectoryEntry,
)

DIRECTORY_FILE_SCHEMA = TypeAdapter(dict[str, ColleagueDirectoryEntry])


class YamlColleagueDirectory:
    def __init__(self, path: Path) -> None:
        self._path = path

    def colleagues(self) -> list[Colleague]:
        entries = DIRECTORY_FILE_SCHEMA.validate_python(
            yaml.safe_load(self._path.read_text(encoding="utf-8")) or {}
        )
        return [
            Colleague(key=str(key), name=entry.name, editor=entry.editor)
            for key, entry in entries.items()
        ]

    def find(self, key: str) -> Colleague | None:
        return next(
            (colleague for colleague in self.colleagues() if colleague.key == key),
            None,
        )
