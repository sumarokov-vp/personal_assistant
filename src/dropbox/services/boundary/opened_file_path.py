import fcntl
import os
import sys
from pathlib import Path

PATH_BUFFER_SIZE = 1024


def opened_file_path(descriptor: int) -> Path:
    if sys.platform == "darwin":
        raw = fcntl.fcntl(descriptor, fcntl.F_GETPATH, bytes(PATH_BUFFER_SIZE))
        return Path(os.fsdecode(raw.split(b"\0", 1)[0]))
    return Path(os.readlink(f"/proc/self/fd/{descriptor}"))
