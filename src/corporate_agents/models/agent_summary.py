from dataclasses import dataclass

from src.corporate_agents.models.agent_layer import AgentLayer


@dataclass(frozen=True)
class AgentSummary:
    name: str
    description: str
    layer: AgentLayer
