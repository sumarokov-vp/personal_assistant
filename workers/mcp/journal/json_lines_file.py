from pathlib import Path


class JsonLinesFile:
    def __init__(self, path: Path) -> None:
        self._path = path

    def append(self, line: str) -> None:
        with self._path.open("a", encoding="utf-8") as journal:
            journal.write(line + "\n")
