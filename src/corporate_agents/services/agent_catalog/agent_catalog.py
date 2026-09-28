import logging
from collections.abc import Sequence
from dataclasses import dataclass

from src.corporate_agents.errors import AgentNotFoundError
from src.corporate_agents.models import (
    AgentDefinition,
    AgentFile,
    AgentSummary,
    agent_name_key,
)
from src.corporate_agents.services.agent_catalog.protocols import IAgentLayer

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _CatalogEntry:
    agent: AgentFile
    source: IAgentLayer


class AgentCatalog:
    def __init__(self, layers: Sequence[IAgentLayer]) -> None:
        self._layers = tuple(layers)

    def get(self, name: str) -> AgentDefinition:
        key = agent_name_key(name)
        entry = next(
            (entry for entry in self._entries() if entry.agent.key == key), None
        )
        if entry is None:
            raise AgentNotFoundError(name)
        agent = entry.agent
        return AgentDefinition(
            name=agent.name,
            description=agent.description,
            instruction=agent.instruction,
            layer=agent.layer,
            version=entry.source.version_of(agent),
            path=agent.path,
        )

    def _entries(self) -> tuple[_CatalogEntry, ...]:
        chosen: dict[str, _CatalogEntry] = {}
        for source in self._layers:
            for agent in source.agents():
                winner = chosen.get(agent.key)
                if winner is not None:
                    logger.warning(
                        "Agent name conflict: «%s» from %s layer (%s) is shadowed by %s layer (%s)",
                        agent.name,
                        agent.layer,
                        agent.path,
                        winner.agent.layer,
                        winner.agent.path,
                    )
                    continue
                chosen[agent.key] = _CatalogEntry(agent=agent, source=source)
        return tuple(sorted(chosen.values(), key=lambda entry: entry.agent.key))

    def list(self) -> list[AgentSummary]:
        return [
            AgentSummary(
                name=entry.agent.name,
                description=entry.agent.description,
                layer=entry.agent.layer,
            )
            for entry in self._entries()
        ]
