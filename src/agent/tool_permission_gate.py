from typing import Any

from claude_agent_sdk import PermissionResult, PermissionResultAllow, PermissionResultDeny, ToolPermissionContext

SANDBOX_NETWORK_ACCESS = "SandboxNetworkAccess"


class ToolPermissionGate:
    async def __call__(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        context: ToolPermissionContext,
    ) -> PermissionResult:
        if tool_name == SANDBOX_NETWORK_ACCESS:
            return PermissionResultAllow()
        return PermissionResultDeny(
            message=(
                f"{tool_name} с такими параметрами запрещён политикой бота: "
                "писать можно только внутри рабочей папки, секреты пользователя закрыты. "
                "Не пытайся обойти запрет другими инструментами."
            )
        )
