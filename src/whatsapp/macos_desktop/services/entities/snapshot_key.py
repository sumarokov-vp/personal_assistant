def parse_snapshot_key(value: str) -> int | None:
    stripped = value.strip()
    return int(stripped) if stripped.isascii() and stripped.isdigit() else None
