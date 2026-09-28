import hashlib
import logging
from pathlib import Path

from src.corporate_agents.models import AgentFile, AgentLayer
from src.corporate_agents.repos.agent_markdown_parser import AgentMarkdownParser
from src.corporate_agents.repos.git_head_reader import GitHeadReader

logger = logging.getLogger(__name__)

AGENTS_SUBDIR = "agents"
REPLACEMENT_CHARACTER = "�"


class AgentDirectory:
    def __init__(
        self,
        root: Path,
        layer: AgentLayer,
        parser: AgentMarkdownParser,
        head_reader: GitHeadReader,
    ) -> None:
        self._root = root
        self._layer = layer
        self._parser = parser
        self._head_reader = head_reader

    def agents(self) -> list[AgentFile]:
        agents_dir = self._root / AGENTS_SUBDIR
        if not agents_dir.is_dir():
            return []
        found: dict[str, AgentFile] = {}
        for path in sorted(agents_dir.glob("*.md")):
            if not path.is_file():
                continue
            agent = self._read(path)
            if agent is None:
                continue
            earlier = found.get(agent.key)
            if earlier is not None:
                logger.warning(
                    "Agent «%s» in %s duplicates %s within %s layer, skipped",
                    agent.name,
                    path,
                    earlier.path,
                    self._layer,
                )
                continue
            found[agent.key] = agent
        return list(found.values())

    def version_of(self, agent: AgentFile) -> str:
        head = self._head_reader.head_of(self._root)
        if head is not None:
            return head
        return f"sha256:{agent.content_sha256}"

    def _read(self, path: Path) -> AgentFile | None:
        data = path.read_bytes()
        text = data.decode("utf-8", errors="replace")
        if REPLACEMENT_CHARACTER in text and REPLACEMENT_CHARACTER.encode() not in data:
            self._log_skip(path, "not UTF-8")
            return None
        parsed = self._parser.parse(text)
        if parsed is None:
            self._log_skip(path, "broken frontmatter")
            return None
        name = parsed.fields.get("name", "").strip()
        description = parsed.fields.get("description", "").strip()
        if not name:
            self._log_skip(path, "no name in frontmatter")
            return None
        if not description:
            self._log_skip(path, "no description in frontmatter")
            return None
        if not parsed.body:
            self._log_skip(path, "empty instruction")
            return None
        return AgentFile(
            name=name,
            description=description,
            instruction=parsed.body,
            layer=self._layer,
            path=path,
            content_sha256=hashlib.sha256(data).hexdigest(),
        )

    def _log_skip(self, path: Path, reason: str) -> None:
        logger.warning("Agent file %s skipped: %s", path, reason)
