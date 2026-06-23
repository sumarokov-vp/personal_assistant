from pathlib import Path

import httpx


class HttpTranscriber:
    def __init__(
        self,
        base_url: str,
        default_language: str = "ru",
        timeout: float = 300.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._default_language = default_language
        self._timeout = timeout

    def __call__(self, audio_path: Path) -> str:
        with audio_path.open("rb") as audio_file:
            response = httpx.post(
                f"{self._base_url}/transcribe",
                files={"file": (audio_path.name, audio_file)},
                data={"language": self._default_language},
                timeout=self._timeout,
            )
        response.raise_for_status()
        return response.json()["text"]
