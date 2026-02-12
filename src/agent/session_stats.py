from dataclasses import dataclass
from typing import Any

from claude_agent_sdk import ResultMessage


@dataclass
class SessionStats:
    model: str = ""
    session_id: str = ""
    total_cost_usd: float = 0.0
    total_turns: int = 0
    total_messages: int = 0
    input_tokens: int = 0
    output_tokens: int = 0

    def update_from_result(self, result: ResultMessage) -> None:
        self.total_cost_usd += result.total_cost_usd or 0.0
        self.total_turns += result.num_turns
        self.total_messages += 1
        if result.usage:
            self.input_tokens += result.usage.get("input_tokens", 0)
            self.output_tokens += result.usage.get("output_tokens", 0)

    def update_from_init(self, data: dict[str, Any]) -> None:
        self.model = data.get("model", "")
        self.session_id = data.get("session_id", "")

    def format(self) -> str:
        lines = [
            f"Model: {self.model}",
            f"Messages: {self.total_messages}",
            f"Turns: {self.total_turns}",
            f"Tokens: {self.input_tokens} in / {self.output_tokens} out",
            f"Cost: ${self.total_cost_usd:.4f}",
        ]
        return "\n".join(lines)
