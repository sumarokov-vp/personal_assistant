from pathlib import Path

from src.corporate_agents.models import AgentLayer
from src.corporate_agents.repos import (
    AgentDirectory,
    AgentMarkdownParser,
    GitHeadReader,
)
from src.corporate_agents.services import AgentCatalog


def build_agent_catalog(
    corporate_dir: Path | None, personal_dir: Path | None
) -> AgentCatalog:
    parser = AgentMarkdownParser()
    head_reader = GitHeadReader()
    layers = [
        AgentDirectory(root, layer, parser, head_reader)
        for root, layer in (
            (corporate_dir, AgentLayer.CORPORATE),
            (personal_dir, AgentLayer.PERSONAL),
        )
        if root is not None
    ]
    return AgentCatalog(layers)
