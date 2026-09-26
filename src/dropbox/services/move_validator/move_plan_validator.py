from collections import Counter
from collections.abc import Sequence
from pathlib import PurePosixPath

from src.dropbox.models.planned_move import PlannedMove
from src.dropbox.services.entities.move_problem import MoveProblem
from src.dropbox.services.move_validator.protocols.i_dropbox_move_checker import (
    IDropboxMoveChecker,
)


class MovePlanValidator:
    def __init__(self, boundary: IDropboxMoveChecker) -> None:
        self._boundary = boundary

    def problems(self, moves: Sequence[PlannedMove]) -> list[MoveProblem]:
        sources = Counter(_key(move.source) for move in moves)
        targets = Counter(_key(move.target) for move in moves)
        problems = []
        for move in moves:
            reason = self._plan_conflict(move, sources, targets) or (
                self._boundary.move_denial(move.source, move.target)
            )
            if reason is not None:
                problems.append(MoveProblem(move=move, reason=reason))
        return problems

    def _plan_conflict(
        self, move: PlannedMove, sources: Counter[str], targets: Counter[str]
    ) -> str | None:
        if sources[_key(move.source)] > 1:
            return f"{move.source} переносится в плане больше одного раза"
        if targets[_key(move.target)] > 1:
            return f"В {move.target} в плане переносится больше одного файла"
        if sources[_key(move.target)] or targets[_key(move.source)]:
            return "Цепочка переносов в одном плане: цель одного переноса — источник другого"
        return None


def _key(path: str) -> str:
    return PurePosixPath(path.strip().strip("/")).as_posix().casefold()
