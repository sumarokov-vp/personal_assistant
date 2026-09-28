from dataclasses import dataclass
from pathlib import Path

from src.corporate_agents.models.agent_layer import AgentLayer


@dataclass(frozen=True)
class AgentFile:
    name: str
    description: str
    instruction: str
    layer: AgentLayer
    path: Path
    content_sha256: str

    @property
    def key(self) -> str:
        return agent_name_key(self.name)


def agent_name_key(name: str) -> str:
    return name.strip().casefold()
