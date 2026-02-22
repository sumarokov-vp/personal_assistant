from os import getenv
from pathlib import Path
from typing import Any

import whisper  # type: ignore[import-untyped]
from pyannote.audio import Pipeline  # type: ignore[import-untyped]


def _find_speaker_for_segment(segment_start: float, segment_end: float, diarization: Any) -> str:
    max_overlap = 0.0
    best_speaker = "Unknown"

    for turn, _, speaker in diarization.itertracks(yield_label=True):
        overlap_start = max(segment_start, turn.start)
        overlap_end = min(segment_end, turn.end)
        overlap = max(0.0, overlap_end - overlap_start)

        if overlap > max_overlap:
            max_overlap = overlap
            best_speaker = speaker

    return best_speaker


def transcribe(audio_path: Path, model: str = "small") -> Path:
    hf_token = getenv("HUGGINGFACE_TOKEN")
    if not hf_token:
        raise ValueError("HUGGINGFACE_TOKEN environment variable is required")

    whisper_model = whisper.load_model(model)
    result: dict[str, Any] = whisper_model.transcribe(str(audio_path), language="ru", verbose=False)
    segments: list[dict[str, Any]] = result["segments"]

    diarization_pipeline: Any = Pipeline.from_pretrained(
        "pyannote/speaker-diarization-3.1",
        token=hf_token,
    )
    diarization = diarization_pipeline(str(audio_path))

    speaker_map: dict[str, int] = {}
    speaker_counter = 0
    lines: list[str] = []
    current_speaker: str | None = None

    for segment in segments:
        seg_start: float = segment["start"]
        seg_end: float = segment["end"]
        raw_speaker = _find_speaker_for_segment(seg_start, seg_end, diarization)

        if raw_speaker not in speaker_map:
            speaker_counter += 1
            speaker_map[raw_speaker] = speaker_counter

        speaker_label = f"Speaker {speaker_map[raw_speaker]}"
        text: str = segment["text"].strip()

        if speaker_label != current_speaker:
            lines.append(f"\n**[{speaker_label}]** {text}")
            current_speaker = speaker_label
        else:
            lines.append(f" {text}")

    output_text = f"# Транскрипция: {audio_path.name}\n" + "".join(lines) + "\n"

    output_path = audio_path.with_suffix(".md")
    output_path.write_text(output_text, encoding="utf-8")

    return output_path
