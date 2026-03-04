from pathlib import Path
from typing import Any

import whisper  # type: ignore[import-untyped]


def transcribe(audio_path: Path, model: str = "small") -> Path:
    whisper_model = whisper.load_model(model)
    result: dict[str, Any] = whisper_model.transcribe(str(audio_path), language="ru", verbose=False)
    segments: list[dict[str, Any]] = result["segments"]

    lines = [segment["text"].strip() + "\n" for segment in segments]

    output_text = f"# Транскрипция: {audio_path.name}\n\n" + "".join(lines) + "\n"

    output_path = audio_path.with_suffix(".md")
    output_path.write_text(output_text, encoding="utf-8")

    return output_path
