import json
from pathlib import PurePosixPath
from typing import ClassVar

from ai_framework import BaseTool, ToolContext
from pydantic import BaseModel, Field

from src.ai_tools.dropbox_save.protocols.i_dropbox_file_saver import (
    IDropboxFileSaver,
)
from src.ai_tools.dropbox_save.protocols.i_work_file_reader import IWorkFileReader
from src.ai_tools.dropbox_save.saved_file_name import saved_file_name
from src.dropbox.services.boundary.dropbox_access_denied_error import (
    DropboxAccessDeniedError,
)
from src.files.work_folder.work_file_not_found_error import WorkFileNotFoundError


class DropboxSaveInput(BaseModel):
    file_id: str = Field(description="file_id из ответа file_take")
    folder: str = Field(
        description=(
            "папка относительно корня Dropbox, как её показывает dropbox_tree; "
            "несуществующая будет создана"
        )
    )
    name: str | None = Field(
        default=None,
        description=(
            "имя файла в Dropbox; не указано — имя файла из рабочей папки, "
            "без расширения — расширение добавится само"
        ),
    )


class DropboxSaveTool(BaseTool):
    name: ClassVar[str] = "dropbox_save"
    description: ClassVar[str] = (
        "Кладёт в Dropbox файл из рабочей папки бота по file_id. Файл сперва забирается "
        "в рабочую папку инструментом file_take — из письма, из Dropbox или вложением "
        "из чата (source=chat), — и его file_id передаётся сюда. Существующий файл не "
        "перезаписывается: при совпадении имени добавляется « (2)». Возвращает path — "
        "итоговый путь; его и называй владельцу. Закрытые части Dropbox и неизвестный "
        "file_id — error."
    )

    Input: ClassVar[type[BaseModel]] = DropboxSaveInput

    def __init__(self, work_files: IWorkFileReader, saver: IDropboxFileSaver) -> None:
        self._work_files = work_files
        self._saver = saver

    def execute(self, input: DropboxSaveInput, context: ToolContext) -> str:  # noqa: A002
        file_id = input.file_id.strip()
        try:
            name = saved_file_name(self._work_files.get(file_id), input.name)
            path = self._saver.save(input.folder, name, self._work_files.read(file_id))
        except (
            WorkFileNotFoundError,
            DropboxAccessDeniedError,
            NotADirectoryError,
            FileExistsError,
        ) as error:
            return json.dumps({"error": str(error)}, ensure_ascii=False)
        return json.dumps(
            {"path": path, "renamed": PurePosixPath(path).name != name},
            ensure_ascii=False,
        )
