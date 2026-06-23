from pathlib import Path
from typing import Any

import whisper  # type: ignore[import-untyped]


def transcribe(audio_path: Path, model: str = "small") -> str:
    whisper_model = whisper.load_model(model)
    result: dict[str, Any] = whisper_model.transcribe(str(audio_path), language="ru", verbose=False)
    segments: list[dict[str, Any]] = result["segments"]

    lines = [segment["text"].strip() for segment in segments]

    return "\n".join(line for line in lines if line)
