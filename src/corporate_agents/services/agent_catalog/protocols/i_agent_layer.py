from typing import Protocol

from src.corporate_agents.models import AgentFile


class IAgentLayer(Protocol):
    def agents(self) -> list[AgentFile]: ...

    def version_of(self, agent: AgentFile) -> str: ...
