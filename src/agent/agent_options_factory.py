import json
from logging import getLogger
from pathlib import Path
from typing import Any

from claude_agent_sdk import ClaudeAgentOptions, McpSdkServerConfig

from src.agent.tool_permission_gate import ToolPermissionGate

logger = getLogger(__name__)

BOT_TOOLS_SERVER_NAME = "bot-tools"

READ_ONLY_TOOLS = ["Read", "Glob", "Grep", "WebFetch", "WebSearch"]
WORKFLOW_TOOLS = ["TodoWrite", "Task", "Agent"]
EDIT_TOOLS = ["Edit", "Write", "NotebookEdit"]
AGENT_CONFIG_FILES = [".claude", ".mcp.json", "CLAUDE.md", "CLAUDE.local.md"]
CLI_ENV_SCRUB = {"CLAUDE_CODE_SUBPROCESS_ENV_SCRUB": "1"}


class AgentOptionsFactory:
    def __init__(
        self,
        workspace_dir: Path,
        protected_paths: list[Path],
        hidden_env_vars: list[str],
        allowed_mcp_servers: list[str],
        sandbox_enabled: bool,
        mcp_server: McpSdkServerConfig | None = None,
    ) -> None:
        self._workspace_dir = workspace_dir.resolve()
        self._protected_paths = [path.resolve() for path in protected_paths]
        self._hidden_env_vars = hidden_env_vars
        self._allowed_mcp_servers = allowed_mcp_servers
        self._sandbox_enabled = sandbox_enabled
        self._mcp_server = mcp_server

    def build(self) -> ClaudeAgentOptions:
        options = ClaudeAgentOptions(
            cwd=str(self._workspace_dir),
            permission_mode="default",
            can_use_tool=ToolPermissionGate(),
            system_prompt={"type": "preset", "preset": "claude_code"},
            tools={"type": "preset", "preset": "claude_code"},
            settings=json.dumps(self._settings()),
            setting_sources=["project"],
            env={**dict.fromkeys(self._hidden_env_vars, ""), **CLI_ENV_SCRUB},
            stderr=lambda line: logger.debug("CLI stderr: %s", line),
        )
        if self._mcp_server is not None:
            options.mcp_servers = {BOT_TOOLS_SERVER_NAME: self._mcp_server}
        return options

    def _allow_rules(self) -> list[str]:
        workspace_rules = [f"{tool}({_rule_path(self._workspace_dir)}/**)" for tool in EDIT_TOOLS]
        bot_tools = [f"mcp__{BOT_TOOLS_SERVER_NAME}"] if self._mcp_server is not None else []
        external_mcp = [f"mcp__{server}" for server in self._allowed_mcp_servers]
        unsandboxed_bash = [] if self._sandbox_enabled else ["Bash"]
        return READ_ONLY_TOOLS + WORKFLOW_TOOLS + workspace_rules + bot_tools + external_mcp + unsandboxed_bash

    def _settings(self) -> dict[str, Any]:
        return {
            "enabledPlugins": {},
            "permissions": {
                "allow": self._allow_rules(),
                "deny": self._deny_rules(),
                "disableBypassPermissionsMode": "disable",
            },
            "sandbox": {
                "enabled": self._sandbox_enabled,
                "failIfUnavailable": True,
                "autoAllowBashIfSandboxed": True,
                "allowUnsandboxedCommands": False,
                "excludedCommands": [],
                "filesystem": {
                    "allowWrite": [str(self._workspace_dir)],
                    "denyWrite": [str(path) for path in self._agent_config_paths()],
                    "denyRead": [str(path) for path in self._protected_paths],
                },
            },
        }

    def _deny_rules(self) -> list[str]:
        read_rules = [
            f"{tool}({pattern})"
            for path in self._protected_paths
            for pattern in _path_patterns(path)
            for tool in ["Read", *EDIT_TOOLS]
        ]
        config_rules = [
            f"{tool}({pattern})"
            for path in self._agent_config_paths()
            for pattern in _path_patterns(path)
            for tool in EDIT_TOOLS
        ]
        return read_rules + config_rules

    def _agent_config_paths(self) -> list[Path]:
        return [self._workspace_dir / name for name in AGENT_CONFIG_FILES]


def _rule_path(path: Path) -> str:
    return f"/{path}"


def _path_patterns(path: Path) -> list[str]:
    return [_rule_path(path), f"{_rule_path(path)}/**"]
