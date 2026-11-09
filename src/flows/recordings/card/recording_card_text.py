from html import escape

BYTES_IN_KB = 1024
BYTES_IN_MB = 1024 * 1024

RECOGNIZE_BUTTON_TEXT = "Да"
DISMISS_BUTTON_TEXT = "Нет"
STALE_CARD_ALERT = "Карточка устарела — перешлите запись заново."
ALREADY_ANSWERED_TEXT = "На эту карточку уже ответили."


class RecordingCardText:
    def question(self, file_name: str, size_bytes: int) -> str:
        return f"Распознать запись <b>{escape(file_name)}</b>, {self.size(size_bytes)}?"

    def recognizing(self, file_name: str, size_bytes: int) -> str:
        return f"Распознаю запись <b>{escape(file_name)}</b>, {self.size(size_bytes)}…"

    def dismissed(self, file_name: str, size_bytes: int) -> str:
        return (
            f"Запись <b>{escape(file_name)}</b>, {self.size(size_bytes)}, не распознаю."
        )

    def too_large(self, file_name: str, size_bytes: int, max_bytes: int) -> str:
        return (
            f"Запись <b>{escape(file_name)}</b> весит {self.size(size_bytes)}, "
            f"а бот принимает записи до {self.size(max_bytes)}: файлы крупнее "
            "Telegram ботам не отдаёт. Пришлите запись покороче или разрежьте "
            "её на части."
        )

    def size(self, size_bytes: int) -> str:
        if size_bytes <= 0:
            return "размер неизвестен"
        if size_bytes < BYTES_IN_MB:
            return f"{max(1, round(size_bytes / BYTES_IN_KB))} КБ"
        megabytes = f"{size_bytes / BYTES_IN_MB:.1f}".removesuffix(".0")
        return f"{megabytes.replace('.', ',')} МБ"
