from urllib.parse import parse_qs, urlsplit

from pydantic import BaseModel, ConfigDict

CDN_HOST = "mmg.whatsapp.net"
EXPIRY_PARAMETER = "oe"
HEX_BASE = 16


class CdnLink(BaseModel):
    model_config = ConfigDict(frozen=True)

    url: str
    expires_at: float | None

    def expired(self, now: float) -> bool:
        return self.expires_at is not None and self.expires_at <= now


def parse_cdn_link(url: str | None) -> CdnLink | None:
    if not url:
        return None
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.hostname != CDN_HOST or parts.port is not None:
        return None
    expiry = parse_qs(parts.query).get(EXPIRY_PARAMETER, [""])[0]
    expires_at = float(int(expiry, HEX_BASE)) if _is_hex(expiry) else None
    return CdnLink(url=url, expires_at=expires_at)


def _is_hex(value: str) -> bool:
    return bool(value) and all(char in "0123456789abcdefABCDEF" for char in value)
