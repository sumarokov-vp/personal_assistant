from src.voice_recognition.errors.voice_recognition_error import VoiceRecognitionError


class RecognitionRequestError(VoiceRecognitionError):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(
            f"Сервис распознавания отклонил запрос (HTTP {status_code}): {detail}"
        )
        self.status_code = status_code
        self.detail = detail
