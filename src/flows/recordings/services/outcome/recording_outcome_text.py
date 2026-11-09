from html import escape

from src.flows.recordings.services.entities.protocol_prompt import ProtocolPrompt


class RecordingOutcomeText:
    def ready(
        self,
        file_name: str,
        transcript_path: str,
        transcript_url: str,
        prompts: list[ProtocolPrompt],
    ) -> str:
        requests = "\n".join(
            f"<code>{escape(prompt.request)}</code>" for prompt in prompts
        )
        return (
            f"Запись <b>{escape(file_name)}</b> распознана, расшифровка — "
            f'<a href="{escape(transcript_url)}">{escape(transcript_path)}</a>.\n\n'
            "Протокол встречи или звонка составит Claude: кнопка ниже откроет его "
            "с готовой просьбой. Если просьба не подставилась — отправьте её сами:\n"
            f"{requests}"
        )

    def failed(self, file_name: str, reason: str) -> str:
        return (
            f"Запись <b>{escape(file_name)}</b> не распознана: {escape(reason)}. "
            "Перешлите её позже."
        )
