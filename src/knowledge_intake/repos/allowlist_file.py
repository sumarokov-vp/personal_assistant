from pathlib import Path

COMMENT_MARK = "#"


class AllowlistFile:
    def __init__(self, path: Path) -> None:
        self._path = path

    def contains(self, email: str) -> bool:
        return email.strip().lower() in self._addresses()

    def _addresses(self) -> set[str]:
        lines = self._path.read_text(encoding="utf-8").splitlines()
        return {
            line.strip().lower()
            for line in lines
            if line.strip() and not line.strip().startswith(COMMENT_MARK)
        }
