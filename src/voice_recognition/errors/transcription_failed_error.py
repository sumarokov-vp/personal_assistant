from src.voice_recognition.errors.voice_recognition_error import VoiceRecognitionError


class TranscriptionFailedError(VoiceRecognitionError):
    def __init__(self, job_id: str, reason: str) -> None:
        super().__init__(f"Распознавание {job_id} упало: {reason}")
        self.job_id = job_id
        self.reason = reason
