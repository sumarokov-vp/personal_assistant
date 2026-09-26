import mimetypes
from pathlib import PurePosixPath

from src.ai_tools.dropbox_save.protocols.i_work_file_info import IWorkFileInfo

EXTENSION_ALIASES = {".jpg": ".jpeg", ".jpeg": ".jpg"}


def saved_file_name(work_file: IWorkFileInfo, requested: str | None) -> str:
    name = (requested or "").strip()
    if not name:
        return _with_extension(work_file.name, work_file)
    if PurePosixPath(name).suffix.casefold() in _own_extensions(work_file):
        return name
    return f"{name}{_extension(work_file)}"


def _with_extension(name: str, work_file: IWorkFileInfo) -> str:
    if PurePosixPath(name).suffix:
        return name
    return f"{name}{_extension(work_file)}"


def _extension(work_file: IWorkFileInfo) -> str:
    suffix = PurePosixPath(work_file.name).suffix
    if suffix:
        return suffix
    return mimetypes.guess_extension(work_file.media_type) or ""


def _own_extensions(work_file: IWorkFileInfo) -> set[str]:
    extensions = {
        _extension(work_file).casefold(),
        (mimetypes.guess_extension(work_file.media_type) or "").casefold(),
    }
    aliases = {EXTENSION_ALIASES.get(extension, "") for extension in extensions}
    return (extensions | aliases) - {""}
