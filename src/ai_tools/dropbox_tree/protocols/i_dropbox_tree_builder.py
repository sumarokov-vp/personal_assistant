from typing import Protocol

from src.dropbox.services.tree.tree_node import TreeNode


class IDropboxTreeBuilder(Protocol):
    def build(
        self, path: str = "", depth: int = 2, include_files: bool = False
    ) -> TreeNode: ...
