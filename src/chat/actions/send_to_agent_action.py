from threading import Lock

from ai_framework import Attachment
from bot_framework import IMessageDeleter, IMessageReplacer, IMessageSender

from src.chat.actions.protocols.i_conversation_ai import IConversationAI
from src.chat.actions.protocols.i_system_prompt_builder import ISystemPromptBuilder

TELEGRAM_MESSAGE_LIMIT = 4096
EMPTY_RESPONSE_TEXT = "Пустой ответ от ассистента"


class SendToAgentAction:
    def __init__(
        self,
        ai: IConversationAI,
        system_prompt_builder: ISystemPromptBuilder,
        message_sender: IMessageSender,
        message_replacer: IMessageReplacer,
        message_deleter: IMessageDeleter,
    ) -> None:
        self.ai = ai
        self.system_prompt_builder = system_prompt_builder
        self.message_sender = message_sender
        self.message_replacer = message_replacer
        self.message_deleter = message_deleter
        self._thread_locks: dict[str, Lock] = {}
        self._thread_locks_guard = Lock()

    def execute(
        self,
        chat_id: int,
        user_id: int,
        text: str,
        thinking_message_id: int,
        attachments: list[Attachment] | None = None,
    ) -> None:
        thread_id = str(user_id)
        with self._thread_lock(thread_id):
            self._ask_and_reply(chat_id, user_id, thread_id, text, thinking_message_id, attachments)

    def _thread_lock(self, thread_id: str) -> Lock:
        with self._thread_locks_guard:
            return self._thread_locks.setdefault(thread_id, Lock())

    def _ask_and_reply(
        self,
        chat_id: int,
        user_id: int,
        thread_id: str,
        text: str,
        thinking_message_id: int,
        attachments: list[Attachment] | None,
    ) -> None:
        self.ai.update_system_prompt(self.system_prompt_builder.build())
        response = self.ai.process_message(
            thread_id=thread_id,
            user_message=text,
            tool_context={"chat_id": chat_id, "user_id": user_id},
            attachments=attachments,
        )
        if response.suppress_response:
            self.message_deleter.delete(chat_id=chat_id, message_id=thinking_message_id)
            return

        content = response.content or ""
        chunks = _split_message(content if content.strip() else EMPTY_RESPONSE_TEXT)

        self.message_replacer.replace(
            chat_id=chat_id,
            message_id=thinking_message_id,
            text=chunks[0],
        )

        for chunk in chunks[1:]:
            self.message_sender.send(chat_id=chat_id, text=chunk)


def _split_message(text: str) -> list[str]:
    if len(text) <= TELEGRAM_MESSAGE_LIMIT:
        return [text]

    chunks: list[str] = []
    while text:
        if len(text) <= TELEGRAM_MESSAGE_LIMIT:
            chunks.append(text)
            break

        split_pos = text.rfind("\n", 0, TELEGRAM_MESSAGE_LIMIT)
        if split_pos == -1:
            split_pos = TELEGRAM_MESSAGE_LIMIT

        chunks.append(text[:split_pos])
        text = text[split_pos:].lstrip("\n")

    return chunks
