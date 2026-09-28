import os
from pathlib import Path
from tempfile import NamedTemporaryFile


class LocalFolderStorage:
    def __init__(self, root: Path) -> None:
        self._root = root

    def read(self, path: str) -> str | None:
        page = self._root / path
        if not page.is_file():
            return None
        return page.read_text(encoding="utf-8")

    def write(self, path: str, content: str, commit_message: str) -> None:
        page = self._root / path
        page.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=page.parent,
            prefix=f".{page.name}.",
            delete=False,
        ) as draft:
            draft.write(content)
        os.replace(draft.name, page)
