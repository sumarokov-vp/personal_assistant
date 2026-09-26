from pathlib import Path, PurePosixPath

from src.wiki.errors.wiki_path_error import WikiPathError

FORBIDDEN_DIRECTORIES = frozenset({".git", ".obsidian"})
WRITABLE_SUFFIX = ".md"


class WikiPathPolicy:
    def __init__(self, root: Path) -> None:
        self._root = root

    def resolve_for_read(self, relative_path: str) -> Path:
        return self._resolve(relative_path)

    def resolve_for_write(self, relative_path: str) -> Path:
        resolved = self._resolve(relative_path)
        if resolved.suffix != WRITABLE_SUFFIX:
            raise WikiPathError(relative_path, "записывать можно только *.md")
        return resolved

    def relative_name(self, path: Path) -> str:
        return path.resolve().relative_to(self._root.resolve()).as_posix()

    def is_readable_page(self, path: Path) -> bool:
        root = self._root.resolve()
        resolved = path.resolve()
        return (
            resolved.suffix == WRITABLE_SUFFIX
            and resolved.is_relative_to(root)
            and not FORBIDDEN_DIRECTORIES.intersection(
                path.relative_to(self._root).parts
            )
            and not FORBIDDEN_DIRECTORIES.intersection(resolved.relative_to(root).parts)
        )

    def _resolve(self, relative_path: str) -> Path:
        requested = PurePosixPath(relative_path.strip())
        if not requested.parts:
            raise WikiPathError(relative_path, "пустой путь")
        if requested.is_absolute():
            raise WikiPathError(
                relative_path, "нужен путь внутри вики, а не абсолютный"
            )
        if ".." in requested.parts:
            raise WikiPathError(relative_path, "выход за пределы вики")
        if FORBIDDEN_DIRECTORIES.intersection(requested.parts):
            raise WikiPathError(relative_path, "служебный каталог .git/.obsidian")
        root = self._root.resolve()
        resolved = (root / requested).resolve()
        if not resolved.is_relative_to(root) or resolved == root:
            raise WikiPathError(relative_path, "ссылка ведёт за пределы вики")
        if FORBIDDEN_DIRECTORIES.intersection(resolved.relative_to(root).parts):
            raise WikiPathError(relative_path, "ссылка ведёт в служебный каталог")
        return resolved
