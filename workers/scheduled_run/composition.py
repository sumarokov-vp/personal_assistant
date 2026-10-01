from logging import getLogger
from pathlib import Path
from threading import Thread
from time import sleep
from zoneinfo import ZoneInfo

from ai_framework import AIApplication, BaseTool, Provider
from ai_framework.protocols.i_attachment_store import IAttachmentStore

from src.agent_notifications.services.text_splitter import TelegramTextSplitter
from src.chat.actions.system_prompt_builder import SystemPromptBuilder
from src.scheduled_runs.repos import PostgresScheduledRunRepository
from src.scheduled_runs.services.due_parser import ScheduleDueParser
from src.scheduled_runs.services.executor import ScheduledRunExecutor
from src.scheduled_runs.services.executor.protocols import ICaseBriefing
from src.scheduled_runs.services.rabbitmq_consumer import RabbitMqScheduleDueConsumer
from workers.scheduled_run.ai_run_model import AiRunModel
from workers.scheduled_run.cases_briefing import CasesBriefing, NoCasesBriefing
from workers.scheduled_run.owner_notifier import SplittingOwnerNotifier
from workers.scheduled_run.protocols import (
    ICaseFeedSource,
    IPlainSender,
    IPromptBuilder,
)
from workers.scheduled_run.run_prompt import ScheduledRunPrompt
from workers.scheduled_run.run_tools import scheduled_run_tools
from workers.scheduled_run.scheduler_settings import SchedulerSettings

logger = getLogger(__name__)

SCHEDULE_RUN_PROMPT_PATH = (
    Path(__file__).parent.parent.parent / "data" / "schedule_run_prompt.txt"
)
SUBSCRIPTION_HAS_NO_API_KEY = ""
RECONNECT_SECONDS = 15


def build_scheduled_run_ai(
    model: str,
    ai_database_url: str,
    bot_tools: list[BaseTool],
    attachment_store: IAttachmentStore | None,
) -> AIApplication:
    tools = scheduled_run_tools(bot_tools)
    logger.info("Scheduled run tools: %s", ", ".join(tool.name for tool in tools))
    return AIApplication(
        api_key=SUBSCRIPTION_HAS_NO_API_KEY,
        provider=Provider.CLAUDE_SDK,
        model=model,
        system_prompt="",
        database_url=ai_database_url,
        tools=tools,
        attachment_store=attachment_store,
    )


def build_scheduled_run_prompt(
    bot_prompt: IPromptBuilder, timezone: ZoneInfo
) -> ScheduledRunPrompt:
    return ScheduledRunPrompt(
        bot_prompt=bot_prompt,
        run_prompt=SystemPromptBuilder(
            template=SCHEDULE_RUN_PROMPT_PATH.read_text(encoding="utf-8"),
            timezone=timezone,
        ),
    )


def build_case_briefing(
    cases: ICaseFeedSource | None, timezone: ZoneInfo
) -> ICaseBriefing:
    if cases is None:
        return NoCasesBriefing()
    return CasesBriefing(cases=cases, timezone=timezone)


def build_scheduled_run_consumer(
    settings: SchedulerSettings,
    database_url: str,
    ai: AIApplication,
    prompt: IPromptBuilder,
    briefing: ICaseBriefing,
    sender: IPlainSender,
    owner_chat_id: int,
) -> RabbitMqScheduleDueConsumer:
    return RabbitMqScheduleDueConsumer(
        amqp_url=settings.amqp_url,
        queue=settings.queue,
        handler=ScheduledRunExecutor(
            scheduler_account=settings.scheduler_account,
            parser=ScheduleDueParser(),
            journal=PostgresScheduledRunRepository(database_url=database_url),
            briefing=briefing,
            model=AiRunModel(
                conversation=ai,
                prompt=prompt,
                tool_context={"chat_id": owner_chat_id, "user_id": owner_chat_id},
            ),
            notifier=SplittingOwnerNotifier(
                sender=sender,
                splitter=TelegramTextSplitter(),
                owner_chat_id=owner_chat_id,
            ),
        ),
    )


def consume_scheduled_runs_forever(
    ai: AIApplication, consumer: RabbitMqScheduleDueConsumer
) -> None:
    with ai:
        while True:
            try:
                consumer.consume()
            except Exception:
                logger.exception("Scheduled runs consumer failed, reconnecting")
            sleep(RECONNECT_SECONDS)


def start_scheduled_runs(
    settings: SchedulerSettings | None,
    database_url: str,
    ai_model: str,
    ai_database_url: str,
    bot_tools: list[BaseTool],
    attachment_store: IAttachmentStore | None,
    bot_prompt: IPromptBuilder,
    cases: ICaseFeedSource | None,
    timezone: ZoneInfo,
    sender: IPlainSender,
    owner_chat_id: int,
) -> Thread | None:
    if settings is None:
        return None
    ai = build_scheduled_run_ai(ai_model, ai_database_url, bot_tools, attachment_store)
    consumer = build_scheduled_run_consumer(
        settings=settings,
        database_url=database_url,
        ai=ai,
        prompt=build_scheduled_run_prompt(bot_prompt, timezone),
        briefing=build_case_briefing(cases, timezone),
        sender=sender,
        owner_chat_id=owner_chat_id,
    )
    thread = Thread(
        target=consume_scheduled_runs_forever,
        args=(ai, consumer),
        name="scheduled-runs",
        daemon=True,
    )
    thread.start()
    logger.info("Scheduled runs consume %s", settings.queue)
    return thread
