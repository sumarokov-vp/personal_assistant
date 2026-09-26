import json
from typing import ClassVar

from ai_framework.entities.tool_context import ToolContext
from ai_framework.protocols.base_tool import BaseTool
from pydantic import BaseModel, Field

from src.ai_tools.dropbox_tree.protocols.i_dropbox_tree_builder import (
    IDropboxTreeBuilder,
)
from src.dropbox.services.boundary.dropbox_access_denied_error import (
    DropboxAccessDeniedError,
)


class DropboxTreeInput(BaseModel):
    path: str = ""
    depth: int = Field(default=2, ge=0, le=5)
    include_files: bool = False


class DropboxTreeTool(BaseTool):
    name: ClassVar[str] = "dropbox_tree"
    description: ClassVar[str] = (
        "Показывает дерево папок Dropbox владельца. "
        "path — папка относительно корня Dropbox (пусто — корень), например 03_home/09_travel. "
        "depth — сколько уровней вложенных папок раскрыть (0–5, по умолчанию 2). "
        "include_files — перечислить имена файлов в раскрытых папках. "
        "У каждой папки есть file_count (файлы прямо в ней) и total_file_count (со вложенными). "
        "Закрытые части Dropbox в дереве не видны; запрос к ним вернёт error."
    )

    Input: ClassVar[type[BaseModel]] = DropboxTreeInput

    def __init__(self, tree_builder: IDropboxTreeBuilder) -> None:
        self._tree_builder = tree_builder

    def execute(self, input: DropboxTreeInput, context: ToolContext) -> str:  # noqa: A002
        try:
            tree = self._tree_builder.build(
                path=input.path,
                depth=input.depth,
                include_files=input.include_files,
            )
        except (
            DropboxAccessDeniedError,
            FileNotFoundError,
            NotADirectoryError,
        ) as error:
            return json.dumps({"error": str(error)}, ensure_ascii=False)
        return tree.model_dump_json()
