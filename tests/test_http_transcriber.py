from pathlib import Path
from unittest.mock import MagicMock, patch

from src.voice_recognition.http_transcriber import HttpTranscriber


class TestHttpTranscriber:
    def test_posts_audio_and_returns_text(self, tmp_path: Path) -> None:
        audio_path = tmp_path / "voice.ogg"
        audio_path.write_bytes(b"audio-bytes")

        response = MagicMock()
        response.json.return_value = {"text": "распознанный текст", "language": "ru"}

        transcriber = HttpTranscriber(base_url="http://service:8000/", default_language="ru")

        with patch("src.voice_recognition.http_transcriber.httpx.post", return_value=response) as post:
            result = transcriber(audio_path)

        assert result == "распознанный текст"
        response.raise_for_status.assert_called_once()

        call = post.call_args
        assert call.args[0] == "http://service:8000/transcribe"
        assert call.kwargs["data"] == {"language": "ru"}
        assert call.kwargs["files"]["file"][0] == "voice.ogg"
        assert call.kwargs["timeout"] == 300.0
