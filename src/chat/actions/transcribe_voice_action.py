import tempfile
from pathlib import Path

from bot_framework import IDocumentDownloader

from src.chat.actions.protocols.i_transcriber import ITranscriber


class TranscribeVoiceAction:
    def __init__(
        self,
        document_downloader: IDocumentDownloader,
        transcriber: ITranscriber,
    ) -> None:
        self.document_downloader = document_downloader
        self.transcriber = transcriber

    def execute(self, file_id: str) -> str:
        audio_bytes = self.document_downloader.download_document(file_id)
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=".ogg", prefix="voice_"
        ) as tmp_file:
            tmp_file.write(audio_bytes)
        audio_path = Path(tmp_file.name)
        try:
            return self.transcriber(audio_path).strip()
        finally:
            audio_path.unlink(missing_ok=True)
