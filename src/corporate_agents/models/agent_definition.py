from dataclasses import dataclass
from pathlib import Path

from src.corporate_agents.models.agent_layer import AgentLayer


@dataclass(frozen=True)
class AgentDefinition:
    name: str
    description: str
    instruction: str
    layer: AgentLayer
    version: str
    path: Path
