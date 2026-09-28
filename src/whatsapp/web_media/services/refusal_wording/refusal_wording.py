REFUSAL_WORDS = {
    "not_linked": (
        "WhatsApp Web на Mac mini отвязан от аккаунта — код перепривязки придёт "
        "в Telegram, его нужно ввести на телефоне"
    ),
    "reupload_timeout": (
        "телефон не прислал файл заново за 2 минуты — проверь, что он в сети"
    ),
    "chat_not_found": "чат не нашёлся в WhatsApp Web",
    "document_not_found": "документ не нашёлся в чате в WhatsApp Web",
    "ui_changed": "изменился интерфейс WhatsApp Web — сценарий скачивания надо чинить",
    "size_mismatch": "WhatsApp Web отдал файл другого размера",
    "unauthorized": "сервис WhatsApp Web не принял ключ бота (WHATSAPP_WEB_TOKEN)",
    "bad_request": "сервис WhatsApp Web не принял запрос бота",
}


def refusal_wording(status: int, code: str, detail: str) -> str:
    words = REFUSAL_WORDS.get(code, f"сервис WhatsApp Web ответил {status}")
    return f"{words} ({detail})" if detail else words
