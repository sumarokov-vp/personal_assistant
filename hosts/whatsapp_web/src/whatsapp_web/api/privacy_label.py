import hashlib

LABEL_LENGTH = 10


def privacy_label(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:LABEL_LENGTH]
