from logging import getLogger
from typing import Any

from src.scheduled_runs.services.executor.model_reply import ModelReply
from workers.scheduled_run.protocols.i_prompt_builder import IPromptBuilder
from workers.scheduled_run.protocols.i_run_conversation import IRunConversation

logger = getLogger(__name__)


class AiRunModel:
    def __init__(
        self,
        conversation: IRunConversation,
        prompt: IPromptBuilder,
        tool_context: dict[str, Any],
    ) -> None:
        self._conversation = conversation
        self._prompt = prompt
        self._tool_context = tool_context

    def answer(self, thread_id: str, request: str) -> ModelReply:
        # Граница с моделью: сбой прогона — не повод терять сообщение, владелец узнаёт тип ошибки
        try:
            self._conversation.update_system_prompt(self._prompt.build())
            response = self._conversation.process_message(
                thread_id=thread_id,
                user_message=request,
                tool_context=self._tool_context,
            )
        except Exception as error:
            logger.exception("Scheduled run model failed in %s", thread_id)
            return ModelReply(text=None, error=type(error).__name__)
        return ModelReply(text=response.content)
