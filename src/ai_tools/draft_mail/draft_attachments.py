from collections.abc import Sequence

from src.ai_tools.draft_mail.draft_file import DraftFile
from src.ai_tools.draft_mail.protocols.i_draft_file import IDraftFile
from src.ai_tools.draft_mail.protocols.i_draft_work_file import IDraftWorkFile
from src.ai_tools.draft_mail.protocols.i_draft_work_files import IDraftWorkFiles
from src.ai_tools.draft_mail.protocols.i_overflow_placer import IOverflowPlacer

BYTES_IN_MEGABYTE = 1024 * 1024
GMAIL_LIMIT_NOTE = "письмо Gmail не больше 25 МБ"


class DraftAttachments[WorkFileT: IDraftWorkFile]:
    def __init__(
        self,
        work_files: IDraftWorkFiles[WorkFileT],
        overflow: IOverflowPlacer[WorkFileT] | None,
    ) -> None:
        self._work_files = work_files
        self._overflow = overflow

    def collect(self, file_ids: Sequence[str]) -> list[DraftFile]:
        files: list[DraftFile] = []
        for file_id in dict.fromkeys(file_id.strip() for file_id in file_ids):
            work_file = self._work_files.get(file_id)
            files.append(
                DraftFile(
                    key=work_file.id,
                    name=work_file.name,
                    media_type=work_file.media_type,
                    content=self._work_files.read(file_id),
                )
            )
        return files

    def settle(
        self,
        files: Sequence[IDraftFile],
        attached: Sequence[str],
        left_out: Sequence[str],
    ) -> list[str]:
        names = {file.key: file.name for file in files}
        lines: list[str] = []
        if attached:
            lines.append(
                "Приложено: " + ", ".join(f"«{names[key]}»" for key in attached)
            )
        lines.extend(self._left_out_line(key) for key in left_out)
        return lines

    def _left_out_line(self, file_id: str) -> str:
        work_file = self._work_files.get(file_id)
        size = f"{work_file.size / BYTES_IN_MEGABYTE:.1f} МБ"
        refused = f"«{work_file.name}» ({size}) не приложен: {GMAIL_LIMIT_NOTE}."
        if self._overflow is None:
            return (
                f"{refused} Dropbox не подключён — файл не сохранён, "
                "его придётся приложить в Gmail вручную."
            )
        path = self._overflow.place(work_file)
        return (
            f"{refused} Файл лежит в Dropbox: {path} "
            "(временная папка, через сутки удалится)."
        )
