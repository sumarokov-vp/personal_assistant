from pathlib import Path

from ai_framework import AIApplication, Provider

from src.knowledge_intake import (
    ImapMailbox,
    IntakeSummary,
    KnowledgeIntakeFactory,
)
from workers.knowledge_intake.ai_knowledge_model import AiKnowledgeModel
from workers.knowledge_intake.intake_run_line import IntakeRunLine
from workers.knowledge_intake.knowledge_intake_env import KnowledgeIntakeEnv
from workers.knowledge_intake.knowledge_intake_job import KnowledgeIntakeJob
from workers.knowledge_intake.protocols.i_owner_notifier import IOwnerNotifier

KNOWLEDGE_INTAKE_PROMPT_PATH = (
    Path(__file__).parent.parent.parent / "data" / "knowledge_intake_prompt.txt"
)
SUBSCRIPTION_HAS_NO_API_KEY = ""
SINGLE_ANSWER_ROUND = 1


def build_knowledge_intake_job(
    env: KnowledgeIntakeEnv, notifier: IOwnerNotifier
) -> KnowledgeIntakeJob:
    return KnowledgeIntakeJob(
        runs=KnowledgeIntakeFactory(
            toolkit=env.toolkit,
            allowlist_path=env.allowlist_path,
            timezone=env.owner_timezone,
        ),
        summary=IntakeSummary(),
        run_line=IntakeRunLine(),
        notifier=notifier,
    )


def build_knowledge_ai(env: KnowledgeIntakeEnv, system_prompt: str) -> AIApplication:
    return AIApplication(
        api_key=SUBSCRIPTION_HAS_NO_API_KEY,
        provider=Provider.CLAUDE_SDK,
        model=env.ai_model,
        system_prompt=system_prompt,
        database_url=env.ai_db_url,
        tools=[],
        max_tool_rounds=SINGLE_ANSWER_ROUND,
    )


def run_knowledge_intake(
    env: KnowledgeIntakeEnv, system_prompt: str, notifier: IOwnerNotifier
) -> str | None:
    job = build_knowledge_intake_job(env, notifier)
    ai = build_knowledge_ai(env, system_prompt)
    with ai, ImapMailbox(env.imap) as mailbox:
        return job.execute(mailbox, AiKnowledgeModel(ai))
