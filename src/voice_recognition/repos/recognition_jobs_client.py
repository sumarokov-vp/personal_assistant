import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx

from src.voice_recognition.errors.recognition_request_error import (
    RecognitionRequestError,
)
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
from src.voice_recognition.models.transcription_job import TranscriptionJob
from src.voice_recognition.models.transcription_status import TranscriptionStatus

ASYNC_PATH = "/transcribe/async"
HEALTH_PATH = "/health"
HTTP_OK = 200
HTTP_ACCEPTED = 202
HTTP_CLIENT_ERROR = 400
HTTP_UNAUTHORIZED = 401
HTTP_FORBIDDEN = 403
HTTP_NOT_FOUND = 404
HTTP_SERVER_ERROR = 500
DEFAULT_CONNECT_TIMEOUT_SECONDS = 10.0
DEFAULT_REQUEST_TIMEOUT_SECONDS = 30.0
DEFAULT_UPLOAD_BYTES_PER_SECOND = 256 * 1024
DEFAULT_POLL_INTERVAL_SECONDS = 10.0
DEFAULT_MAX_WAIT_SECONDS = 3 * 60 * 60.0


class RecognitionJobsClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        default_language: str | None = "ru",
        connect_timeout: float = DEFAULT_CONNECT_TIMEOUT_SECONDS,
        request_timeout: float = DEFAULT_REQUEST_TIMEOUT_SECONDS,
        upload_bytes_per_second: int = DEFAULT_UPLOAD_BYTES_PER_SECOND,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._headers = {"X-API-Key": api_key}
        self._default_language = default_language
        self._connect_timeout = connect_timeout
        self._request_timeout = request_timeout
        self._upload_bytes_per_second = upload_bytes_per_second
        self._transport = transport
        self._sleep = sleep
        self._clock = clock

    def ensure_available(self) -> None:
        response = self._send("GET", HEALTH_PATH, self._timeout(self._request_timeout))
        if response.status_code != HTTP_OK:
            raise RecognitionUnavailableError(
                f"{HEALTH_PATH} ответил HTTP {response.status_code}"
            )

    def submit(self, audio_path: Path, language: str | None = None) -> str:
        self.ensure_available()
        chosen_language = language or self._default_language
        form = {"language": chosen_language} if chosen_language else {}
        with audio_path.open("rb") as audio_file:
            response = self._send(
                "POST",
                ASYNC_PATH,
                self._upload_timeout(audio_path.stat().st_size),
                files={"file": (audio_path.name, audio_file)},
                data=form,
            )
        if response.status_code != HTTP_ACCEPTED:
            raise _error_for(response, job_id="")
        return str(response.json()["job_id"])

    def job(self, job_id: str) -> TranscriptionJob:
        response = self._send(
            "GET", f"{ASYNC_PATH}/{job_id}", self._timeout(self._request_timeout)
        )
        if response.status_code != HTTP_OK:
            raise _error_for(response, job_id=job_id)
        return TranscriptionJob.model_validate(response.json())

    def wait_for_result(
        self,
        job_id: str,
        poll_interval: float = DEFAULT_POLL_INTERVAL_SECONDS,
        max_wait: float = DEFAULT_MAX_WAIT_SECONDS,
    ) -> dict[str, Any]:
        started = self._clock()
        job = self.job(job_id)
        while not job.status.is_finished:
            waited = self._clock() - started
            if waited >= max_wait:
                raise TranscriptionWaitExceededError(job_id, waited)
            self._sleep(poll_interval)
            job = self.job(job_id)
        return _result_of(job)

    def _upload_timeout(self, size_bytes: int) -> httpx.Timeout:
        transfer_seconds = size_bytes / self._upload_bytes_per_second
        return self._timeout(self._request_timeout + transfer_seconds)

    def _timeout(self, seconds: float) -> httpx.Timeout:
        return httpx.Timeout(
            seconds, connect=self._connect_timeout, pool=self._connect_timeout
        )

    def _send(
        self,
        method: str,
        path: str,
        timeout: httpx.Timeout,
        files: dict[str, Any] | None = None,
        data: dict[str, str] | None = None,
    ) -> httpx.Response:
        with httpx.Client(
            timeout=timeout, headers=self._headers, transport=self._transport
        ) as client:
            try:
                return client.request(
                    method, f"{self._base_url}{path}", files=files, data=data
                )
            except httpx.TransportError as error:
                raise RecognitionUnavailableError(type(error).__name__) from error


def _result_of(job: TranscriptionJob) -> dict[str, Any]:
    if job.status is TranscriptionStatus.FAILED or job.result is None:
        raise TranscriptionFailedError(
            job.job_id, job.error or "сервис не отдал result"
        )
    return job.result


def _detail(response: httpx.Response) -> str:
    if not response.headers.get("content-type", "").startswith("application/json"):
        return response.text[:200]
    body = response.json()
    if isinstance(body, dict) and "detail" in body:
        return str(body["detail"])
    return str(body)[:200]


def _error_for(response: httpx.Response, job_id: str) -> Exception:
    status = response.status_code
    if status in (HTTP_UNAUTHORIZED, HTTP_FORBIDDEN):
        return RecognitionUnauthorizedError(status)
    if status == HTTP_NOT_FOUND and job_id:
        return TranscriptionJobNotFoundError(job_id)
    if status >= HTTP_SERVER_ERROR:
        return RecognitionUnavailableError(f"HTTP {status}")
    return RecognitionRequestError(status, _detail(response))
