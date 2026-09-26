from pathlib import Path

from src.dropbox.services.tree.protocols.i_dropbox_directory_boundary import (
    IDropboxDirectoryBoundary,
)
from src.dropbox.services.tree.tree_node import TreeNode


class DropboxTree:
    def __init__(self, boundary: IDropboxDirectoryBoundary) -> None:
        self._boundary = boundary

    def build(
        self, path: str = "", depth: int = 2, include_files: bool = False
    ) -> TreeNode:
        directory = self._boundary.resolve(path)
        if not directory.is_dir():
            raise NotADirectoryError(f"{path} — не папка Dropbox")
        return self._node(directory, depth, include_files)

    def _node(self, directory: Path, depth: int, include_files: bool) -> TreeNode:
        children = self._boundary.visible_children(directory)
        subdirectories = [child for child in children if _is_real_directory(child)]
        files = [child for child in children if child.is_file()]
        folders = [
            self._node(child, depth - 1, include_files) for child in subdirectories
        ]
        return TreeNode(
            name=directory.name,
            path=self._boundary.relative(directory),
            file_count=len(files),
            total_file_count=len(files)
            + sum(folder.total_file_count for folder in folders),
            folders=folders if depth > 0 else [],
            files=[file.name for file in files] if include_files and depth >= 0 else [],
        )


def _is_real_directory(path: Path) -> bool:
    return path.is_dir() and not path.is_symlink()
