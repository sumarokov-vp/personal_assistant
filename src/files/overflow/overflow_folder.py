from src.files.overflow.protocols.i_overflow_write_boundary import (
    IOverflowWriteBoundary,
)
from src.files.overflow.protocols.i_work_file_content import IWorkFileContent
from src.files.work_folder.work_file import WorkFile

OVERFLOW_FOLDER_NAME = "Personal Assistant"


class OverflowFolder:
    def __init__(
        self, boundary: IOverflowWriteBoundary, work_files: IWorkFileContent
    ) -> None:
        self._boundary = boundary
        self._work_files = work_files

    def place(self, work_file: WorkFile) -> str:
        return self._boundary.write_new_file(
            OVERFLOW_FOLDER_NAME, work_file.name, self._work_files.read(work_file.id)
        )
