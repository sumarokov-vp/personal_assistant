from dataclasses import dataclass

from src.ai_tools.file_take.protocols.i_file_source import IFileSource


@dataclass(frozen=True)
class RegisteredFileSource:
    key: str
    hint: str
    source: IFileSource
