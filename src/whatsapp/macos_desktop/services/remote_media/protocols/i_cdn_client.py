from typing import Protocol

from src.whatsapp.macos_desktop.models.cdn_download import CdnDownload


class ICdnClient(Protocol):
    def download(self, url: str, max_bytes: int) -> CdnDownload: ...
