from html import escape


class RecordingOutcomeText:
    def ready(self, file_name: str, transcript_path: str, transcript_url: str) -> str:
        return (
            f"Запись <b>{escape(file_name)}</b> распознана, расшифровка — "
            f'<a href="{escape(transcript_url)}">{escape(transcript_path)}</a>.\n\n'
            "Протокол составлю сам и пришлю сюда текстом и PDF — выберите вид кнопкой."
        )

    def failed(self, file_name: str, reason: str) -> str:
        return (
            f"Запись <b>{escape(file_name)}</b> не распознана: {escape(reason)}. "
            "Перешлите её позже."
        )
