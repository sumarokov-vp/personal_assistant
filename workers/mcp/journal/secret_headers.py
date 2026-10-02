MASKED_HEADER_VALUE = "***"
SECRET_HEADER_MARKERS = (
    "auth",
    "cookie",
    "token",
    "secret",
    "api-key",
    "apikey",
    "password",
)


def mask_secret_headers(headers: dict[str, str]) -> dict[str, str]:
    return {
        name: MASKED_HEADER_VALUE if _is_secret(name) else value
        for name, value in headers.items()
    }


def _is_secret(name: str) -> bool:
    lowered = name.lower()
    return any(marker in lowered for marker in SECRET_HEADER_MARKERS)
