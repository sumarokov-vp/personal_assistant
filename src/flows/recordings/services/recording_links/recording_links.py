from pathlib import PurePosixPath
from urllib.parse import quote

from src.flows.recordings.services.entities.protocol_prompt import ProtocolPrompt

STORAGE_HOME_URL = "https://www.dropbox.com/home"
CLAUDE_NEW_CHAT_URL = "https://claude.ai/new"
PROTOCOL_KINDS = (
    ("Протокол встречи", "протокол встречи"),
    ("Протокол звонка", "протокол звонка"),
)


class RecordingLinks:
    def transcript_url(self, transcript_path: str) -> str:
        path = PurePosixPath(transcript_path)
        folder = "" if path.parent == PurePosixPath(".") else path.parent.as_posix()
        return f"{STORAGE_HOME_URL}/{quote(folder)}?preview={quote(path.name, safe='')}"

    def protocol_prompts(self, transcript_path: str) -> list[ProtocolPrompt]:
        return [
            self._prompt(
                title, f"Сделай {kind} по расшифровке записи «{transcript_path}»"
            )
            for title, kind in PROTOCOL_KINDS
        ]

    def _prompt(self, title: str, request: str) -> ProtocolPrompt:
        return ProtocolPrompt(
            title=title,
            request=request,
            url=f"{CLAUDE_NEW_CHAT_URL}?q={quote(request, safe='')}",
        )
