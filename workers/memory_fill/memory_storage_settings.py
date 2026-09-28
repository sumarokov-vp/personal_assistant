from dataclasses import dataclass
from os import getenv
from pathlib import Path

from workers.memory_fill.memory_storage_kind import MemoryStorageKind

MEMORY_STORAGE_VARIABLE = "MEMORY_STORAGE"
MEMORY_DIR_VARIABLE = "MEMORY_DIR"
DEFAULT_MEMORY_DIR = Path.home() / ".local" / "share" / "personal_assistant" / "memory"


@dataclass(frozen=True)
class MemoryStorageSettings:
    kind: MemoryStorageKind
    local_dir: Path


def read_memory_storage_settings() -> MemoryStorageSettings:
    raw_kind = (getenv(MEMORY_STORAGE_VARIABLE) or MemoryStorageKind.LOCAL).strip()
    known = {kind.value for kind in MemoryStorageKind}
    if raw_kind not in known:
        raise ValueError(
            f"{MEMORY_STORAGE_VARIABLE}={raw_kind!r} is unknown, expected one of {sorted(known)}"
        )
    return MemoryStorageSettings(
        kind=MemoryStorageKind(raw_kind),
        local_dir=Path(getenv(MEMORY_DIR_VARIABLE) or DEFAULT_MEMORY_DIR).expanduser(),
    )
