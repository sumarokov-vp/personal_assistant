from pathlib import PurePath

from telebot.types import Audio, Document, Message

from src.flows.recordings.handlers.recording_file import RecordingFile

AUDIO_EXTENSIONS = frozenset({".m4a", ".mp3", ".wav", ".ogg", ".aac"})
AUDIO_MIME_PREFIX = "audio/"
DEFAULT_RECORDING_NAME = "запись"


class RecordingFileDetector:
    def is_recording_document(self, message: Message) -> bool:
        document = message.document
        return document is not None and self._is_audio_document(document)

    def recording_of(self, message: Message) -> RecordingFile | None:
        if message.audio is not None:
            return self._from_audio(message.audio)
        document = message.document
        if document is not None and self._is_audio_document(document):
            return self._from_document(document)
        return None

    def _is_audio_document(self, document: Document) -> bool:
        mime_type = (document.mime_type or "").lower()
        extension = PurePath(document.file_name or "").suffix.lower()
        return mime_type.startswith(AUDIO_MIME_PREFIX) or extension in AUDIO_EXTENSIONS

    def _from_audio(self, audio: Audio) -> RecordingFile:
        return RecordingFile(
            file_id=audio.file_id,
            file_name=audio.file_name or audio.title or DEFAULT_RECORDING_NAME,
            size_bytes=audio.file_size or 0,
        )

    def _from_document(self, document: Document) -> RecordingFile:
        return RecordingFile(
            file_id=document.file_id,
            file_name=document.file_name or DEFAULT_RECORDING_NAME,
            size_bytes=document.file_size or 0,
        )
