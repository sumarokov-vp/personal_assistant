from typing import Protocol

from claude_agent_sdk import ClaudeAgentOptions


class IAgentOptionsFactory(Protocol):
    def build(self) -> ClaudeAgentOptions: ...
