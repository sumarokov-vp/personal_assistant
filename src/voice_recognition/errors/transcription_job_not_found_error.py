from src.voice_recognition.errors.voice_recognition_error import VoiceRecognitionError


class TranscriptionJobNotFoundError(VoiceRecognitionError):
    def __init__(self, job_id: str) -> None:
        super().__init__(
            f"Задание распознавания {job_id} неизвестно сервису: очередь сервиса в "
            "памяти, после перезапуска задание потеряно — запись нужно отправить заново"
        )
        self.job_id = job_id
