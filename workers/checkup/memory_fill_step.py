from workers.memory_fill.composition import run_memory_fill
from workers.memory_fill.memory_fill_env import MemoryFillEnv
from workers.memory_fill.memory_fill_report import MemoryFillReport


class MemoryFillStep:
    def __init__(self, env: MemoryFillEnv, prompt_template: str) -> None:
        self._env = env
        self._prompt_template = prompt_template

    def execute(self) -> MemoryFillReport:
        return run_memory_fill(self._env, self._prompt_template)
