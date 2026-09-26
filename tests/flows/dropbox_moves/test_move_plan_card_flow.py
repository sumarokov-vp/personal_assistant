import json
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
from ai_framework.entities.tool_context import ToolContext
from bot_framework.core.entities.bot_callback import BotCallback
from bot_framework.core.entities.bot_message import BotMessage
from bot_framework.core.entities.keyboard import Keyboard
from bot_framework.core.entities.parse_mode import ParseMode
from bot_framework.core.protocols.i_callback_handler import ICallbackHandler

from src.ai_tools.dropbox_propose_moves import DropboxProposeMovesTool
from src.ai_tools.dropbox_propose_moves.tool import (
    DropboxMoveInput,
    DropboxProposeMovesInput,
)
from src.ai_tools.dropbox_undo_moves import DropboxUndoMovesTool
from src.ai_tools.dropbox_undo_moves.tool import DropboxUndoMovesInput
from src.dropbox.models.move_plan_status import MovePlanStatus
from src.dropbox.services.boundary.dropbox_access_policy import DropboxAccessPolicy
from src.dropbox.services.boundary.dropbox_boundary import DropboxBoundary
from src.dropbox.services.move_canceller.move_plan_canceller import MovePlanCanceller
from src.dropbox.services.move_executor.move_plan_executor import MovePlanExecutor
from src.dropbox.services.move_planner.move_planner import MovePlanner
from src.dropbox.services.move_rollback.move_plan_rollback import MovePlanRollback
from src.dropbox.services.move_validator.move_plan_validator import MovePlanValidator
from src.flows.dropbox_moves import (
    CancelMovePlanHandler,
    ExecuteMovePlanHandler,
    MovePlanCallbackGuard,
    MovePlanCardPresenter,
    MovePlanCardText,
    RollbackMovePlanHandler,
)
from tests.dropbox.in_memory_dropbox_journal import InMemoryDropboxJournal
from tests.dropbox.in_memory_move_plan_store import InMemoryMovePlanStore

PHRASES = Path(__file__).parents[3] / "data" / "phrases.json"
OWNER_ID = 42
STRANGER_ID = 7
CHAT_ID = 100
CARD_MESSAGE_ID = 555
TELEGRAM_CALLBACK_DATA_LIMIT = 64
TICKET = "Itinerary_ALA_CNX.pdf"
TRAVEL = "03_home/09_travel/thailand_2026-11"
ROOT_MOVES = [
    ("ride_1.mp4", "03_home/02_cycling/ride_1.mp4"),
    ("ride_2.mp4", "03_home/02_cycling/ride_2.mp4"),
    (TICKET, f"{TRAVEL}/{TICKET}"),
]


class JsonPhraseRepo:
    def __init__(self) -> None:
        self._phrases = json.loads(PHRASES.read_text(encoding="utf-8"))

    def get_phrase(self, key: str, language_code: str) -> str:
        return self._phrases[key][language_code]


class RecordingChat:
    def __init__(self) -> None:
        self.cards: list[tuple[str, Keyboard | None]] = []
        self.alerts: list[str | None] = []

    def send(
        self,
        chat_id: int,
        text: str,
        parse_mode: ParseMode = ParseMode.HTML,
        keyboard: Keyboard | None = None,
        flow_name: str | None = None,
    ) -> BotMessage:
        return self._record(chat_id, text, keyboard)

    def send_media_group(
        self, chat_id: int, photo_urls: list[str], caption: str | None = None
    ) -> None:
        raise AssertionError("карточка плана не шлёт фото")

    def send_markdown_as_html(
        self,
        chat_id: int,
        text: str,
        keyboard: Keyboard | None = None,
        flow_name: str | None = None,
    ) -> BotMessage:
        return self._record(chat_id, text, keyboard)

    def replace(
        self,
        chat_id: int,
        message_id: int,
        text: str,
        parse_mode: ParseMode = ParseMode.HTML,
        keyboard: Keyboard | None = None,
        flow_name: str | None = None,
    ) -> BotMessage:
        return self._record(chat_id, text, keyboard)

    def _record(self, chat_id: int, text: str, keyboard: Keyboard | None) -> BotMessage:
        self.cards.append((text, keyboard))
        return BotMessage(chat_id=chat_id, message_id=CARD_MESSAGE_ID)

    def answer(
        self, callback_query_id: str, text: str | None = None, show_alert: bool = False
    ) -> None:
        self.alerts.append(text)

    def buttons(self) -> dict[str, str]:
        keyboard = self.cards[-1][1]
        if keyboard is None:
            return {}
        return {
            button.text: button.callback_data for row in keyboard.rows for button in row
        }


class MoveCardKit:
    def __init__(self, root: Path) -> None:
        boundary = DropboxBoundary(root, DropboxAccessPolicy())
        self.plans = InMemoryMovePlanStore()
        journal = InMemoryDropboxJournal()
        validator = MovePlanValidator(boundary)
        phrases = JsonPhraseRepo()
        self.chat = RecordingChat()
        card = MovePlanCardPresenter(
            self.chat, self.chat, MovePlanCardText(phrases, "ru"), phrases, "ru"
        )
        guard = MovePlanCallbackGuard(self.chat, self.plans, phrases, "ru")
        self.propose = DropboxProposeMovesTool(MovePlanner(validator, self.plans), card)
        self.undo = DropboxUndoMovesTool(self.plans, card)
        self.handlers: list[ICallbackHandler] = [
            ExecuteMovePlanHandler(
                self.chat,
                guard,
                MovePlanExecutor(self.plans, validator, boundary, journal),
                card,
            ),
            CancelMovePlanHandler(
                self.chat, guard, MovePlanCanceller(self.plans), card
            ),
            RollbackMovePlanHandler(
                self.chat, guard, MovePlanRollback(self.plans, boundary, journal), card
            ),
        ]

    def propose_root_cleanup(self) -> dict[str, Any]:
        moves = [DropboxMoveInput(source=s, target=t) for s, t in ROOT_MOVES]
        return json.loads(
            self.propose.execute(
                DropboxProposeMovesInput(moves=moves),
                ToolContext({"chat_id": CHAT_ID, "user_id": OWNER_ID}),
            )
        )

    def press(self, button_text: str, user_id: int = OWNER_ID) -> None:
        data = self.chat.buttons()[button_text]
        callback = BotCallback(
            id="cb",
            user_id=user_id,
            data=data,
            message_id=CARD_MESSAGE_ID,
            message_chat_id=CHAT_ID,
        )
        handler = next(h for h in self.handlers if data.startswith(h.prefix))
        handler.handle(callback)


@pytest.fixture
def root(tmp_path: Path) -> Path:
    for name in ("ride_1.mp4", "ride_2.mp4", TICKET):
        (tmp_path / name).write_bytes(name.encode())
    for folder in ("Vault", "01_work", "Apps/HealthFit", "vault_selftest_1", TRAVEL):
        (tmp_path / folder).mkdir(parents=True)
    return tmp_path


@pytest.fixture
def kit(root: Path) -> MoveCardKit:
    return MoveCardKit(root)


def _root_files_in_place(root: Path) -> bool:
    return all((root / source).is_file() for source, _ in ROOT_MOVES)


def _files_moved(root: Path) -> bool:
    return all(
        (root / target).is_file() and not (root / source).exists()
        for source, target in ROOT_MOVES
    )


def test_nothing_moves_until_execute_then_rollback_returns_files(
    kit: MoveCardKit, root: Path
):
    result = kit.propose_root_cleanup()

    assert result["moves"] == 3
    assert set(kit.chat.buttons()) == {"Выполнить", "Отмена"}
    assert _root_files_in_place(root)

    kit.press("Выполнить")

    assert _files_moved(root)
    assert set(kit.chat.buttons()) == {"Откатить"}

    kit.press("Откатить")

    assert _root_files_in_place(root)
    assert kit.chat.buttons() == {}


def test_stranger_press_changes_nothing(kit: MoveCardKit, root: Path):
    kit.propose_root_cleanup()

    kit.press("Выполнить", user_id=STRANGER_ID)

    assert _root_files_in_place(root)
    assert kit.chat.alerts == ["Этот план принадлежит другому пользователю."]


def test_cancel_leaves_files_and_second_press_is_refused(kit: MoveCardKit, root: Path):
    kit.propose_root_cleanup()
    execute_data = kit.chat.buttons()["Выполнить"]

    kit.press("Отмена")
    kit.handlers[0].handle(
        BotCallback(
            id="cb",
            user_id=OWNER_ID,
            data=execute_data,
            message_id=CARD_MESSAGE_ID,
            message_chat_id=CHAT_ID,
        )
    )

    assert _root_files_in_place(root)
    assert kit.chat.alerts[-1] == "План отменён."


def test_undo_tool_offers_rollback_card_without_moving(kit: MoveCardKit, root: Path):
    plan_id = kit.propose_root_cleanup()["plan_id"]
    kit.press("Выполнить")

    offer = json.loads(
        kit.undo.execute(
            DropboxUndoMovesInput(plan_id=plan_id),
            ToolContext({"chat_id": CHAT_ID, "user_id": OWNER_ID}),
        )
    )

    assert "error" not in offer
    assert _files_moved(root)
    kit.press("Откатить")
    assert _root_files_in_place(root)
    plan = kit.plans.get(UUID(offer["plan_id"]))
    assert plan is not None
    assert plan.status == MovePlanStatus.ROLLED_BACK


@pytest.mark.parametrize(
    ("source", "target"),
    [("Apps/HealthFit", "03_home/HealthFit"), ("ride_1.mp4", "Vault/ride_1.mp4")],
)
def test_forbidden_plan_sends_no_card(
    kit: MoveCardKit, root: Path, source: str, target: str
):
    result = json.loads(
        kit.propose.execute(
            DropboxProposeMovesInput(
                moves=[DropboxMoveInput(source=source, target=target)]
            ),
            ToolContext({"chat_id": CHAT_ID, "user_id": OWNER_ID}),
        )
    )

    assert "error" in result
    assert kit.chat.cards == []


def test_callback_data_fits_telegram_limit(kit: MoveCardKit):
    kit.propose_root_cleanup()

    assert all(
        len(data.encode()) <= TELEGRAM_CALLBACK_DATA_LIMIT
        for data in kit.chat.buttons().values()
    )
