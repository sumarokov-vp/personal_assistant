from src.voice_recognition.errors.voice_recognition_error import VoiceRecognitionError


class RecognitionUnauthorizedError(VoiceRecognitionError):
    def __init__(self, status_code: int) -> None:
        super().__init__(f"Сервис распознавания отверг ключ (HTTP {status_code})")
        self.status_code = status_code
