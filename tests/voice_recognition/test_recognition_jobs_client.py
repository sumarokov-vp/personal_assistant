import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import pytest

from src.voice_recognition.errors.recognition_unauthorized_error import (
    RecognitionUnauthorizedError,
)
from src.voice_recognition.errors.recognition_unavailable_error import (
    RecognitionUnavailableError,
)
from src.voice_recognition.errors.transcription_failed_error import (
    TranscriptionFailedError,
)
from src.voice_recognition.errors.transcription_job_not_found_error import (
    TranscriptionJobNotFoundError,
)
from src.voice_recognition.errors.transcription_wait_exceeded_error import (
    TranscriptionWaitExceededError,
)
from src.voice_recognition.models.transcription_status import TranscriptionStatus
from src.voice_recognition.repos.recognition_jobs_client import RecognitionJobsClient

BASE_URL = "http://recognition.test"
API_KEY = "pa-recognition-key"
JOB_ID = "6f1c2a3b-job"

RAW_RESULT: dict[str, Any] = {
    "text": " Добрый день. Начнём.",
    "language": "ru",
    "duration": 3725.48,
    "model": "large-v3",
    "segments": [
        {
            "id": 0,
            "seek": 0,
            "start": 0.0,
            "end": 2.4,
            "text": " Добрый день.",
            "tokens": [50364, 3401],
            "temperature": 0.0,
            "avg_logprob": -0.21,
            "compression_ratio": 1.1,
            "no_speech_prob": 0.01,
            "words": [
                {"word": "Добрый", "start": 0.0, "end": 0.6, "probability": 0.98}
            ],
        },
        {"id": 1, "start": 3725.0, "end": 3725.48, "text": " Начнём.", "extra": None},
    ],
    "custom_vendor_field": {"nested": [1, 2.5, "x"]},
}

type Responder = Callable[[httpx.Request], httpx.Response]


class Recorder:
    def __init__(self, responder: Responder) -> None:
        self.requests: list[httpx.Request] = []
        self._responder = responder

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return self._responder(request)


def job_payload(status: str, **extra: Any) -> dict[str, Any]:
    return {"job_id": JOB_ID, "status": status, "result": None, "error": None, **extra}


def client_for(recorder: Recorder, **kwargs: Any) -> RecognitionJobsClient:
    return RecognitionJobsClient(
        BASE_URL, API_KEY, transport=httpx.MockTransport(recorder), **kwargs
    )


def healthy(then: Responder) -> Responder:
    def respond(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/health":
            return httpx.Response(200, json={"status": "ok"})
        return then(request)

    return respond


@pytest.fixture
def audio(tmp_path: Path) -> Path:
    path = tmp_path / "meeting.m4a"
    path.write_bytes(b"m4a-bytes" * 100)
    return path


class TestSubmit:
    def test_posts_multipart_with_key_and_returns_job_id(self, audio: Path) -> None:
        recorder = Recorder(
            healthy(lambda _: httpx.Response(202, json={"job_id": JOB_ID}))
        )

        job_id = client_for(recorder).submit(audio)

        assert job_id == JOB_ID
        health, post = recorder.requests
        assert health.url.path == "/health"
        assert post.method == "POST"
        assert str(post.url) == f"{BASE_URL}/transcribe/async"
        assert post.headers["X-API-Key"] == API_KEY
        body = post.read()
        assert b'name="file"; filename="meeting.m4a"' in body
        assert b"m4a-bytes" in body
        assert b'name="language"\r\n\r\nru' in body

    def test_language_overrides_default(self, audio: Path) -> None:
        recorder = Recorder(
            healthy(lambda _: httpx.Response(202, json={"job_id": JOB_ID}))
        )

        client_for(recorder).submit(audio, language="en")

        assert b'name="language"\r\n\r\nen' in recorder.requests[1].read()

    def test_upload_timeout_grows_with_file_size(self, tmp_path: Path) -> None:
        big = tmp_path / "long.m4a"
        big.write_bytes(b"0" * 1_000_000)
        recorder = Recorder(
            healthy(lambda _: httpx.Response(202, json={"job_id": JOB_ID}))
        )

        client_for(
            recorder, request_timeout=30.0, upload_bytes_per_second=10_000
        ).submit(big)

        timeouts = recorder.requests[1].extensions["timeout"]
        assert timeouts["write"] == pytest.approx(130.0)
        assert timeouts["read"] == pytest.approx(130.0)
        assert timeouts["connect"] == pytest.approx(10.0)


class TestJob:
    @pytest.mark.parametrize("status", ["pending", "processing"])
    def test_running_statuses(self, status: str) -> None:
        recorder = Recorder(lambda _: httpx.Response(200, json=job_payload(status)))

        job = client_for(recorder).job(JOB_ID)

        assert job.status == TranscriptionStatus(status)
        assert not job.status.is_finished
        assert job.result is None
        assert str(recorder.requests[0].url) == f"{BASE_URL}/transcribe/async/{JOB_ID}"
        assert recorder.requests[0].headers["X-API-Key"] == API_KEY

    def test_completed_keeps_raw_result_without_losing_fields(self) -> None:
        wire = json.dumps(job_payload("completed", result=RAW_RESULT))
        recorder = Recorder(
            lambda _: httpx.Response(
                200, content=wire, headers={"content-type": "application/json"}
            )
        )

        job = client_for(recorder).job(JOB_ID)

        assert job.status is TranscriptionStatus.COMPLETED
        assert job.result == RAW_RESULT
        assert job.result == json.loads(wire)["result"]

    def test_failed_carries_error(self) -> None:
        recorder = Recorder(
            lambda _: httpx.Response(200, json=job_payload("failed", error="CUDA OOM"))
        )

        job = client_for(recorder).job(JOB_ID)

        assert job.status is TranscriptionStatus.FAILED
        assert job.error == "CUDA OOM"


class TestWaitForResult:
    def test_polls_until_completed_and_returns_raw_result(self) -> None:
        answers = iter(
            [
                job_payload("pending"),
                job_payload("processing"),
                job_payload("completed", result=RAW_RESULT),
            ]
        )
        recorder = Recorder(lambda _: httpx.Response(200, json=next(answers)))
        sleeps: list[float] = []

        result = client_for(
            recorder, sleep=sleeps.append, clock=lambda: 0.0
        ).wait_for_result(JOB_ID, poll_interval=7.0)

        assert result == RAW_RESULT
        assert sleeps == [7.0, 7.0]
        assert len(recorder.requests) == 3

    def test_failed_raises_with_service_error(self) -> None:
        recorder = Recorder(
            lambda _: httpx.Response(200, json=job_payload("failed", error="bad audio"))
        )

        with pytest.raises(TranscriptionFailedError) as raised:
            client_for(recorder).wait_for_result(JOB_ID)

        assert raised.value.job_id == JOB_ID
        assert raised.value.reason == "bad audio"

    def test_gives_up_after_max_wait(self) -> None:
        recorder = Recorder(
            lambda _: httpx.Response(200, json=job_payload("processing"))
        )
        now = iter([0.0, 50.0, 100.0])

        with pytest.raises(TranscriptionWaitExceededError):
            client_for(
                recorder, sleep=lambda _: None, clock=lambda: next(now)
            ).wait_for_result(JOB_ID, max_wait=100.0)


class TestErrors:
    def test_network_error_is_unavailable(self, audio: Path) -> None:
        def refuse(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("connection refused", request=request)

        with pytest.raises(RecognitionUnavailableError):
            client_for(Recorder(refuse)).submit(audio)

    def test_timeout_is_unavailable(self) -> None:
        def hang(request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("timed out", request=request)

        with pytest.raises(RecognitionUnavailableError):
            client_for(Recorder(hang)).job(JOB_ID)

    def test_unhealthy_service_is_unavailable_and_audio_not_sent(
        self, audio: Path
    ) -> None:
        recorder = Recorder(lambda _: httpx.Response(503, json={"status": "loading"}))

        with pytest.raises(RecognitionUnavailableError) as raised:
            client_for(recorder).submit(audio)

        assert "503" in raised.value.reason
        assert [r.url.path for r in recorder.requests] == ["/health"]

    @pytest.mark.parametrize("status", [401, 403])
    def test_rejected_key(self, audio: Path, status: int) -> None:
        recorder = Recorder(
            healthy(
                lambda _: httpx.Response(status, json={"detail": "Invalid API key"})
            )
        )

        with pytest.raises(RecognitionUnauthorizedError) as raised:
            client_for(recorder).submit(audio)

        assert raised.value.status_code == status

    def test_unknown_job_after_service_restart(self) -> None:
        recorder = Recorder(
            lambda _: httpx.Response(404, json={"detail": "Job not found"})
        )

        with pytest.raises(TranscriptionJobNotFoundError) as raised:
            client_for(recorder).job(JOB_ID)

        assert raised.value.job_id == JOB_ID
