from importlib.util import find_spec

from src.chat.actions.protocols.i_transcriber import ITranscriber
from src.voice_recognition.http_transcriber import HttpTranscriber
from src.voice_recognition.native_transcriber import NativeTranscriber

HTTP_MODE = "http"
NATIVE_MODE = "native"


def build_transcriber(
    mode: str,
    http_base_url: str,
    http_api_key: str | None,
    whisper_model: str,
) -> ITranscriber:
    if mode == HTTP_MODE:
        return HttpTranscriber(base_url=http_base_url, api_key=http_api_key)

    if mode == NATIVE_MODE:
        if find_spec("whisper") is None:
            raise ValueError(
                f"VOICE_RECOGNITION_MODE={NATIVE_MODE} требует пакет openai-whisper. "
                "Установите его: uv sync --extra whisper"
            )
        return NativeTranscriber(model_name=whisper_model)

    raise ValueError(
        f"Unknown VOICE_RECOGNITION_MODE: {mode!r}. Expected {HTTP_MODE!r} or {NATIVE_MODE!r}"
    )
