from typing import Any

import pytest

from src.voice_recognition.services.timecoded_transcript.timecoded_transcript import (
    TimecodedTranscript,
)


def result_of(*segments: tuple[float, str]) -> dict[str, Any]:
    return {
        "text": "".join(text for _, text in segments),
        "segments": [
            {"id": i, "start": start, "end": start + 1.0, "text": text, "tokens": [1]}
            for i, (start, text) in enumerate(segments)
        ],
    }


LONG_RESULT = result_of(
    *[(i * 37.5, f" Фраза номер {i}, сказанная на встрече.") for i in range(200)]
)


class TestText:
    def test_lines_with_hours_minutes_seconds(self) -> None:
        transcript = TimecodedTranscript(
            result_of((0.0, " Добрый день."), (65.9, " Начнём."), (3725.2, "  Итоги. "))
        )

        assert transcript.text == (
            "[00:00:00] Добрый день.\n[00:01:05] Начнём.\n[01:02:05] Итоги.\n"
        )

    def test_skips_empty_segments_and_missing_segments(self) -> None:
        assert TimecodedTranscript(result_of((0.0, "  "), (1.0, " Да."))).text == (
            "[00:00:01] Да.\n"
        )
        assert TimecodedTranscript({"text": ""}).text == ""


class TestParts:
    @pytest.mark.parametrize("max_chars", [60, 500, 4000, 40_000])
    def test_parts_glue_back_into_whole_text(self, max_chars: int) -> None:
        transcript = TimecodedTranscript(LONG_RESULT)

        parts = transcript.parts(max_chars)

        assert "".join(parts) == transcript.text
        assert all(len(part) <= max_chars for part in parts)

    def test_split_only_on_segment_boundary(self) -> None:
        transcript = TimecodedTranscript(LONG_RESULT)
        lines = transcript.text.splitlines(keepends=True)

        parts = transcript.parts(500)

        assert len(parts) > 1
        assert all(part.startswith("[") and part.endswith("\n") for part in parts)
        assert sum(len(part.splitlines()) for part in parts) == len(lines)

    def test_segment_longer_than_limit_stays_whole_in_own_part(self) -> None:
        long_phrase = " " + "очень длинная реплика " * 10
        transcript = TimecodedTranscript(
            result_of((0.0, " Коротко."), (5.0, long_phrase), (9.0, " Ещё."))
        )

        parts = transcript.parts(40)

        assert "".join(parts) == transcript.text
        assert parts[1] == f"[00:00:05] {long_phrase.strip()}\n"
        assert len(parts) == 3

    def test_whole_text_fits_into_one_part(self) -> None:
        transcript = TimecodedTranscript(result_of((0.0, " Да."), (1.0, " Нет.")))

        assert transcript.parts(1000) == [transcript.text]
