from string import hexdigits
from uuid import UUID

PLAN_ID_HEX_LENGTH = 32


class MovePlanCallback:
    def __init__(self, prefix: str) -> None:
        self.prefix = prefix

    def data(self, plan_id: UUID) -> str:
        return f"{self.prefix}{plan_id.hex}"

    def plan_id(self, data: str | None) -> UUID | None:
        if data is None or not data.startswith(self.prefix):
            return None
        plan_hex = data.removeprefix(self.prefix)
        if len(plan_hex) != PLAN_ID_HEX_LENGTH or not all(
            char in hexdigits for char in plan_hex
        ):
            return None
        return UUID(hex=plan_hex)
