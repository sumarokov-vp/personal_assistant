MEDIA_KEY_BYTES = 32
PROTOBUF_FIELD_ONE_BYTES = 0x0A


def extract_media_key(blob: bytes | None) -> bytes | None:
    if blob is None:
        return None
    if len(blob) == MEDIA_KEY_BYTES:
        return blob
    header = bytes((PROTOBUF_FIELD_ONE_BYTES, MEDIA_KEY_BYTES))
    if blob.startswith(header) and len(blob) >= len(header) + MEDIA_KEY_BYTES:
        return blob[len(header) : len(header) + MEDIA_KEY_BYTES]
    return None
