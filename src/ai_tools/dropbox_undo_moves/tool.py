import json
from typing import ClassVar
from uuid import UUID

from ai_framework.entities.tool_context import ToolContext
from ai_framework.protocols.base_tool import BaseTool
from pydantic import BaseModel

from src.ai_tools.dropbox_undo_moves.protocols.i_move_plan_reader import (
    IMovePlanReader,
)
from src.ai_tools.dropbox_undo_moves.protocols.i_rollback_offer_sender import (
    IRollbackOfferSender,
)
from src.dropbox.models.move_plan_status import MovePlanStatus


class DropboxUndoMovesInput(BaseModel):
    plan_id: UUID


class DropboxUndoMovesTool(BaseTool):
    name: ClassVar[str] = "dropbox_undo_moves"
    description: ClassVar[str] = (
        "Предлагает откатить выполненный план переносов Dropbox. plan_id — тот, что "
        "вернул dropbox_propose_moves. Сам ничего не возвращает: в чат уходит карточка "
        "плана с кнопкой «Откатить», файлы возвращаются только по нажатию владельца. "
        "Откатывается план целиком; перенос, чей файл уже сдвинули или чьё прежнее место "
        "занято, будет пропущен с причиной. Невыполненный, отменённый или уже откаченный "
        "план вернёт error."
    )

    Input: ClassVar[type[BaseModel]] = DropboxUndoMovesInput

    def __init__(
        self, plans: IMovePlanReader, offer_sender: IRollbackOfferSender
    ) -> None:
        self._plans = plans
        self._offer_sender = offer_sender

    def execute(self, input: DropboxUndoMovesInput, context: ToolContext) -> str:  # noqa: A002
        plan = self._plans.get(input.plan_id)
        if plan is None or plan.owner_id != context.user_id:
            return _error(f"Плана переносов {input.plan_id} нет")
        if plan.status != MovePlanStatus.EXECUTED:
            return _error(
                f"План {plan.id} в статусе {plan.status.value}, "
                "откатить можно только выполненный"
            )
        self._offer_sender.send_rollback_offer(chat_id=context.chat_id, plan=plan)
        return json.dumps(
            {
                "plan_id": str(plan.id),
                "card": "Карточка с кнопкой «Откатить» отправлена в чат; файлы не тронуты до нажатия",
            },
            ensure_ascii=False,
        )


def _error(message: str) -> str:
    return json.dumps({"error": message}, ensure_ascii=False)
