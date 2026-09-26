from importlib import import_module
from pathlib import Path
from typing import Any


class NativeTranscriber:
    def __init__(self, model_name: str = "small", default_language: str = "ru") -> None:
        self._model_name = model_name
        self._default_language = default_language
        self._model: Any = None

    def __call__(self, audio_path: Path) -> str:
        result: dict[str, Any] = self._model_or_loaded().transcribe(
            str(audio_path),
            language=self._default_language,
            verbose=False,
        )
        segments: list[dict[str, Any]] = result["segments"]
        lines = [segment["text"].strip() for segment in segments]

        return "\n".join(line for line in lines if line)

    def _model_or_loaded(self) -> Any:
        if self._model is None:
            whisper = import_module("whisper")
            self._model = whisper.load_model(self._model_name)
        return self._model
