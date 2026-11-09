from src.voice_recognition.errors.voice_recognition_error import VoiceRecognitionError


class RecognitionUnavailableError(VoiceRecognitionError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"Сервис распознавания недоступен: {reason}")
        self.reason = reason
