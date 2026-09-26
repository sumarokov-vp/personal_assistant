import json
from typing import ClassVar

from ai_framework.entities.tool_context import ToolContext
from ai_framework.protocols.base_tool import BaseTool
from pydantic import BaseModel, Field

from src.ai_tools.dropbox_propose_moves.protocols.i_move_plan_card_sender import (
    IMovePlanCardSender,
)
from src.ai_tools.dropbox_propose_moves.protocols.i_move_plan_proposer import (
    IMovePlanProposer,
)
from src.dropbox.models.planned_move import PlannedMove


class DropboxMoveInput(BaseModel):
    source: str = Field(description="Что переносится: путь относительно корня Dropbox")
    target: str = Field(
        description="Куда: полный новый путь вместе с именем файла, относительно корня Dropbox"
    )


class DropboxProposeMovesInput(BaseModel):
    moves: list[DropboxMoveInput] = Field(min_length=1)


class DropboxProposeMovesTool(BaseTool):
    name: ClassVar[str] = "dropbox_propose_moves"
    description: ClassVar[str] = (
        "Предлагает владельцу план переносов и переименований в Dropbox. Сам ничего не "
        "переносит: план сохраняется и уходит в чат карточкой с кнопками «Выполнить» и "
        "«Отмена», переносит только нажатие владельца. moves — список {source, target}, "
        "пути относительно корня Dropbox; target — полный новый путь с именем файла, "
        "недостающие папки создадутся. Переименование — перенос в ту же папку под другим "
        "именем. План принимается только целиком: если хоть один перенос невозможен "
        "(файла нет, цель занята, Apps/, закрытая часть, ключевой файл) — вернётся error "
        "и problems с причинами, карточки не будет; исправь план и предложи снова. "
        "При успехе вернётся plan_id — он нужен для отката через dropbox_undo_moves."
    )

    Input: ClassVar[type[BaseModel]] = DropboxProposeMovesInput

    def __init__(
        self, proposer: IMovePlanProposer, card_sender: IMovePlanCardSender
    ) -> None:
        self._proposer = proposer
        self._card_sender = card_sender

    def execute(self, input: DropboxProposeMovesInput, context: ToolContext) -> str:  # noqa: A002
        proposal = self._proposer.propose(
            owner_id=context.user_id,
            moves=[
                PlannedMove(source=move.source, target=move.target)
                for move in input.moves
            ],
        )
        if proposal.plan is None:
            return json.dumps(
                {
                    "error": "План не принят, ничего не отправлено",
                    "problems": [
                        {
                            "source": problem.move.source,
                            "target": problem.move.target,
                            "reason": problem.reason,
                        }
                        for problem in proposal.problems
                    ],
                },
                ensure_ascii=False,
            )
        self._card_sender.send_proposal(chat_id=context.chat_id, plan=proposal.plan)
        return json.dumps(
            {
                "plan_id": str(proposal.plan.id),
                "moves": len(proposal.plan.moves),
                "card": "Карточка плана отправлена в чат; файлы не тронуты до нажатия «Выполнить»",
            },
            ensure_ascii=False,
        )
