from src.voice_recognition.errors.voice_recognition_error import VoiceRecognitionError


class TranscriptionWaitExceededError(VoiceRecognitionError):
    def __init__(self, job_id: str, waited_seconds: float) -> None:
        super().__init__(
            f"Распознавание {job_id} не закончилось за {waited_seconds:.0f} с — "
            "задание у сервиса живо, опрос можно продолжить"
        )
        self.job_id = job_id
        self.waited_seconds = waited_seconds
