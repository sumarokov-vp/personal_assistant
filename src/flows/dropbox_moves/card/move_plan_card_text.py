from collections.abc import Sequence
from html import escape

from bot_framework.domain.language_management.repos.protocols.i_phrase_repo import (
    IPhraseRepo,
)

from src.dropbox.models.move_plan import MovePlan
from src.dropbox.models.planned_move import PlannedMove
from src.dropbox.services.entities.move_problem import MoveProblem
from src.dropbox.services.move_executor.move_plan_execution import MovePlanExecution
from src.dropbox.services.move_rollback.move_plan_rollback_result import (
    MovePlanRollbackResult,
)

MAX_CARD_LINES = 30


class MovePlanCardText:
    def __init__(self, phrase_repo: IPhraseRepo, language_code: str) -> None:
        self._phrase_repo = phrase_repo
        self._language_code = language_code

    def proposal(self, plan: MovePlan) -> str:
        return self._card(
            self._phrase("dropbox_moves.card.proposal_title", count=len(plan.moves)),
            self._move_lines(plan.moves),
            self._phrase("dropbox_moves.card.proposal_hint"),
        )

    def execution(self, execution: MovePlanExecution) -> str:
        if execution.problems:
            return self._card(
                self._phrase("dropbox_moves.card.execution_refused_title"),
                self._problem_lines(execution.problems),
                self._phrase("dropbox_moves.card.proposal_hint"),
            )
        return self._card(
            self._phrase(
                "dropbox_moves.card.executed_title", count=len(execution.moved)
            ),
            self._move_lines(execution.moved),
            self._phrase("dropbox_moves.card.executed_hint"),
        )

    def rollback(self, result: MovePlanRollbackResult) -> str:
        returned = [
            PlannedMove(source=move.target, target=move.source)
            for move in result.rolled_back
        ]
        text = self._card(
            self._phrase(
                "dropbox_moves.card.rolled_back_title", count=len(result.rolled_back)
            ),
            self._move_lines(returned),
        )
        if not result.skipped:
            return text
        skipped = self._card(
            self._phrase("dropbox_moves.card.rollback_skipped_title"),
            self._problem_lines(result.skipped),
        )
        return f"{text}\n\n{skipped}"

    def cancelled(self, plan: MovePlan) -> str:
        return self._card(
            self._phrase("dropbox_moves.card.cancelled_title", count=len(plan.moves)),
            self._move_lines(plan.moves),
        )

    def rollback_offer(self, plan: MovePlan) -> str:
        return self._card(
            self._phrase(
                "dropbox_moves.card.rollback_offer_title", count=len(plan.moves)
            ),
            self._move_lines(plan.moves),
            self._phrase("dropbox_moves.card.rollback_offer_hint"),
        )

    def _card(self, title: str, lines: list[str], hint: str | None = None) -> str:
        parts = [f"<b>{escape(title)}</b>", "\n".join(lines)]
        if hint is not None:
            parts.append(escape(hint))
        return "\n\n".join(part for part in parts if part)

    def _move_lines(self, moves: Sequence[PlannedMove]) -> list[str]:
        return self._limited(
            [f"{escape(move.source)} → {escape(move.target)}" for move in moves]
        )

    def _problem_lines(self, problems: Sequence[MoveProblem]) -> list[str]:
        return self._limited(
            [
                f"{escape(problem.move.source)} → {escape(problem.move.target)}: "
                f"{escape(problem.reason)}"
                for problem in problems
            ]
        )

    def _limited(self, lines: list[str]) -> list[str]:
        if len(lines) <= MAX_CARD_LINES:
            return lines
        rest = len(lines) - MAX_CARD_LINES
        return [
            *lines[:MAX_CARD_LINES],
            escape(self._phrase("dropbox_moves.card.more", count=rest)),
        ]

    def _phrase(self, key: str, count: int | None = None) -> str:
        phrase = self._phrase_repo.get_phrase(
            key=key, language_code=self._language_code
        )
        if count is None:
            return phrase
        return phrase.format(count=count)
