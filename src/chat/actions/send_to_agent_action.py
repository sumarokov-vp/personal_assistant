from bot_framework import IMessageReplacer, IMessageSender
from src.agent.protocols.i_agent_client import IAgentClient

TELEGRAM_MESSAGE_LIMIT = 4096


class SendToAgentAction:
    def __init__(
        self,
        agent_client: IAgentClient,
        message_sender: IMessageSender,
        message_replacer: IMessageReplacer,
    ) -> None:
        self.agent_client = agent_client
        self.message_sender = message_sender
        self.message_replacer = message_replacer

    def execute(
        self,
        chat_id: int,
        user_id: int,
        text: str,
        thinking_message_id: int,
    ) -> None:
        response = self.agent_client.send_message(user_id, chat_id, text)
        if not response.strip():
            response = "Пустой ответ от агента"
        chunks = _split_message(response)

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
