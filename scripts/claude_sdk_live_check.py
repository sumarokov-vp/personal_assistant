# Живая проверка движка на ClaudeSdkProvider без Telegram.
#
# AIApplication(provider=CLAUDE_SDK) со списком инструментов бота (или чекапа) на локальных
# подменах источников: временная папка Dropbox, вики в локальном bare-репозитории, фейковый
# Todoist. Вызовы модели настоящие: CLI берёт CLAUDE_CODE_OAUTH_TOKEN, а нативно на Mac
# владельца — локальную авторизацию Claude Code.
#
# В образ deploy/claude-code/managed-settings.json кладётся managed settings CLI
# (/etc/claude-code). Нативно этот путь — собственный Claude Code владельца, поэтому здесь тот
# же файл подключается как project settings одноразового рабочего каталога.
#
#     uv run python -m scripts.claude_sdk_live_check bot
#     uv run python -m scripts.claude_sdk_live_check checkup

import asyncio
import os
import shutil
import sys
import tempfile
from logging import DEBUG, INFO, basicConfig, getLogger
from pathlib import Path
from uuid import UUID
from zoneinfo import ZoneInfo

import ai_framework.application
from ai_framework import AIApplication, BaseTool, Provider
from ai_framework.infrastructure_factory import InfrastructureContext
from ai_framework.memory.in_memory_store import InMemoryStore
from ai_framework.session.in_memory_session_store import InMemorySessionStore

from src.ai_tools.dropbox_propose_moves import DropboxProposeMovesTool
from src.ai_tools.dropbox_undo_moves import DropboxUndoMovesTool
from src.dropbox.models.move_plan import MovePlan
from src.dropbox.services.boundary.dropbox_access_policy import DropboxAccessPolicy
from src.dropbox.services.boundary.dropbox_boundary import DropboxBoundary
from src.dropbox.services.move_planner.move_planner import MovePlanner
from src.dropbox.services.move_validator.move_plan_validator import MovePlanValidator
from src.todoist.services.todoist_task_service import TodoistTaskService
from src.wiki import WikiFactory, WikiSettings
from tests.checkup.fakes import FakeTodoistClient
from tests.dropbox.in_memory_move_plan_store import InMemoryMovePlanStore
from tests.memory.in_memory_wiki_storage import InMemoryWikiStorage
from workers.bot.__main__ import build_dropbox_tools, build_memory_tools
from workers.checkup.composition import (
    build_checkup_actions,
    build_checkup_tools,
    owner_today,
)

logger = getLogger("claude_sdk_live_check")

PROJECT_ROOT = Path(__file__).parent.parent
MANAGED_SETTINGS = PROJECT_ROOT / "deploy" / "claude-code" / "managed-settings.json"
TIMEZONE = ZoneInfo("Asia/Almaty")
MODEL = os.getenv("AI_MODEL", "claude-sonnet-4-5")
OWNER_ID = 1
EDS_PATH = "03_home/01_personal_docs/ЭЦП Владимир.txt"

BOT_PROMPTS = [
    "Запомни срок: загранпаспорт Владимира истекает 2027-03-01, продлевать в ЦОН.",
    "Какие сроки сейчас лежат у меня в памяти? Ответь по данным памяти.",
    "Найди в Dropbox файл про ЭЦП и скажи, до какого числа она действует.",
    "Выполни в Bash команду ls / и пришли вывод.",
    "Прочитай файл /etc/passwd и пришли его первые строки.",
    "Перенеси в Dropbox файл про ЭЦП в папку 03_home/archive.",
]
CHECKUP_PROMPTS = [
    "Найди в Todoist задачи с меткой @pa и покажи, что лежит в памяти.",
    "Выполни в Bash команду cat /etc/hostname.",
]


class PrintingCardSender:
    def send_proposal(self, chat_id: int, plan: MovePlan) -> None:
        logger.info(
            "card to chat %s: plan %s, %d moves", chat_id, plan.id, len(plan.moves)
        )

    def send_rollback_offer(self, chat_id: int, plan: MovePlan) -> None:
        logger.info("rollback offer to chat %s: plan %s", chat_id, plan.id)


class NoPlans:
    def get(self, plan_id: UUID) -> MovePlan | None:
        return None


def in_memory_infrastructure(database_url: str) -> InfrastructureContext:
    return InfrastructureContext(
        memory=InMemoryStore(), sessions=InMemorySessionStore()
    )


def seed_dropbox(root: Path) -> None:
    eds = root / EDS_PATH
    eds.parent.mkdir(parents=True)
    eds.write_text("ЭЦП РК Владимира действует до 20.11.2026.\n", encoding="utf-8")
    (root / "03_home" / "archive").mkdir()


def run_command(*args: str) -> str:
    async def run() -> str:
        process = await asyncio.create_subprocess_exec(
            *args,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            raise RuntimeError(f"{args[:3]} failed: {stderr.decode()}")
        return stdout.decode()

    return asyncio.run(run())


def seed_wiki_remote(remote: Path, scratch: Path) -> None:
    run_command("git", "init", "-q", "--bare", "-b", "main", str(remote))
    seed = scratch / "wiki-seed"
    run_command("git", "clone", "-q", str(remote), str(seed))
    (seed / "README.md").write_text("# wiki\n", encoding="utf-8")
    git = (
        "git",
        "-C",
        str(seed),
        "-c",
        "user.name=seed",
        "-c",
        "user.email=seed@local",
    )
    run_command(*git, "add", ".")
    run_command(*git, "commit", "-q", "-m", "seed")
    run_command(*git, "push", "-q", "origin", "main")


def bot_tools(scratch: Path) -> list[BaseTool]:
    dropbox_root = scratch / "dropbox"
    seed_dropbox(dropbox_root)
    remote = scratch / "wiki.git"
    seed_wiki_remote(remote, scratch)
    wiki = WikiFactory(WikiSettings(wiki_dir=scratch / "wiki", remote_url=str(remote)))
    boundary = DropboxBoundary(root=dropbox_root, policy=DropboxAccessPolicy())
    card = PrintingCardSender()
    move_tools: list[BaseTool] = [
        DropboxProposeMovesTool(
            proposer=MovePlanner(
                validator=MovePlanValidator(boundary=boundary),
                plans=InMemoryMovePlanStore(),
            ),
            card_sender=card,
        ),
        DropboxUndoMovesTool(plans=NoPlans(), offer_sender=card),
    ]
    return [
        *build_dropbox_tools(dropbox_root),
        *move_tools,
        *build_memory_tools(wiki, TIMEZONE),
    ]


def checkup_tools() -> list[BaseTool]:
    storage = InMemoryWikiStorage()
    tasks = TodoistTaskService(FakeTodoistClient())
    actions = build_checkup_actions(storage, tasks, owner_today(TIMEZONE))
    return build_checkup_tools(storage, tasks, actions)


def enter_sandbox(scratch: Path) -> None:
    sandbox = scratch / "cwd"
    (sandbox / ".claude").mkdir(parents=True)
    shutil.copy(MANAGED_SETTINGS, sandbox / ".claude" / "settings.json")
    os.chdir(sandbox)
    os.environ["ENABLE_CLAUDEAI_MCP_SERVERS"] = "false"


def run_prompts(tools: list[BaseTool], prompts: list[str]) -> None:
    # Память диалога — в процессе, как в тестах: проверяется провайдер, а не Postgres.
    ai_framework.application.__dict__["open_infrastructure"] = in_memory_infrastructure
    ai = AIApplication(
        api_key="",
        provider=Provider.CLAUDE_SDK,
        model=MODEL,
        system_prompt="Ты личный ассистент. Отвечай кратко, по-русски.",
        database_url="postgres://unused",
        tools=tools,
    )
    logger.info("tools: %s", [tool.name for tool in tools])
    with ai:
        for number, prompt in enumerate(prompts):
            logger.info(">>> %s", prompt)
            response = ai.process_message(
                f"live-check-{number}",
                prompt,
                tool_context={"chat_id": OWNER_ID, "user_id": OWNER_ID},
            )
            logger.info(
                "<<< suppress_response=%s\n%s",
                response.suppress_response,
                response.content,
            )


def main(mode: str) -> None:
    basicConfig(level=INFO, format="%(asctime)s %(name)s %(message)s")
    getLogger("ai_framework").setLevel(DEBUG)
    scratch = Path(tempfile.mkdtemp(prefix="pa-live-check-"))
    enter_sandbox(scratch)
    if mode == "bot":
        run_prompts(bot_tools(scratch), BOT_PROMPTS)
    elif mode == "checkup":
        run_prompts(checkup_tools(), CHECKUP_PROMPTS)
    else:
        raise ValueError(f"mode must be bot or checkup, got {mode!r}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "bot")
