import httpx

from src.whatsapp.macos_desktop.models.cdn_download import CdnDownload

DEFAULT_TIMEOUT_SECONDS = 60.0
OK = 200


class WhatsAppCdnClient:
    def __init__(self, timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS) -> None:
        self._timeout = timeout_seconds

    def download(self, url: str, max_bytes: int) -> CdnDownload:
        with httpx.stream(
            "GET", url, timeout=self._timeout, follow_redirects=False
        ) as response:
            if response.status_code != OK:
                return CdnDownload(
                    status=response.status_code, content=b"", oversized=False
                )
            received = bytearray()
            for chunk in response.iter_bytes():
                received.extend(chunk)
                if len(received) > max_bytes:
                    return CdnDownload(
                        status=response.status_code, content=b"", oversized=True
                    )
            return CdnDownload(
                status=response.status_code, content=bytes(received), oversized=False
            )
