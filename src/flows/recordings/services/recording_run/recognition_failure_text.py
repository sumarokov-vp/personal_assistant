from src.voice_recognition.errors import (
    RecognitionUnauthorizedError,
    RecognitionUnavailableError,
    TranscriptionFailedError,
    TranscriptionJobNotFoundError,
    TranscriptionWaitExceededError,
    VoiceRecognitionError,
)


class RecognitionFailureText:
    def reason(self, error: VoiceRecognitionError) -> str:
        if isinstance(error, RecognitionUnavailableError):
            return "сервис распознавания недоступен"
        if isinstance(error, RecognitionUnauthorizedError):
            return "сервис распознавания не принял ключ бота"
        if isinstance(error, TranscriptionJobNotFoundError):
            return "сервис распознавания потерял задание — похоже, перезапускался"
        if isinstance(error, TranscriptionFailedError):
            return f"сервис распознавания не справился: {error.reason}"
        if isinstance(error, TranscriptionWaitExceededError):
            return "распознавание не закончилось за отведённое время"
        return f"сервис распознавания ответил ошибкой: {error}"
