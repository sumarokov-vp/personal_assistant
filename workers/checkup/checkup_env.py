import tempfile
from dataclasses import dataclass, replace
from os import getenv
from pathlib import Path

from workers.memory_fill.memory_fill_env import (
    MemoryFillEnv,
    read_memory_fill_env,
    require_env,
)

DEFAULT_MAX_TOOL_ROUNDS = 40
DEFAULT_WIKI_DIR = Path(tempfile.gettempdir()) / "checkup_wiki"


@dataclass(frozen=True)
class CheckupEnv:
    memory_fill: MemoryFillEnv
    todoist_token: str
    max_tool_rounds: int


def read_checkup_env() -> CheckupEnv:
    memory_fill = read_memory_fill_env()
    wiki_dir = Path(getenv("CHECKUP_WIKI_DIR", str(DEFAULT_WIKI_DIR)))
    return CheckupEnv(
        memory_fill=replace(
            memory_fill, wiki=replace(memory_fill.wiki, wiki_dir=wiki_dir)
        ),
        todoist_token=require_env("TODOIST_TOKEN"),
        max_tool_rounds=int(
            getenv("CHECKUP_MAX_TOOL_ROUNDS", str(DEFAULT_MAX_TOOL_ROUNDS))
        ),
    )
