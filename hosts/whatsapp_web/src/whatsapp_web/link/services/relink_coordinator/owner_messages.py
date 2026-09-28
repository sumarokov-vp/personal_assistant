from datetime import datetime

LINK_PATH = "Связанные устройства → Привязать устройство → «Связать по номеру телефона»"

UNLINKED = "WhatsApp Web на Mac mini отвязан — файлы, удалённые с сервера WhatsApp, бот не достанет."
UNLINKED_NO_PHONE = (
    UNLINKED
    + " Номера телефона нет в файле секретов сервиса — перепривязать кодом не могу, "
    "нужна привязка руками."
)
RELINKED = "WhatsApp Web снова привязан — файлы, удалённые с сервера WhatsApp, бот снова достаёт."
NOT_LINKED_RUNNING = (
    "WhatsApp Web не привязан: перепривязка идёт, код придёт владельцу в Telegram."
)
NOT_LINKED_NO_PHONE = (
    "WhatsApp Web не привязан, а номера телефона для перепривязки кодом у сервиса нет — "
    "нужна привязка руками."
)


def owner_time(moment: datetime) -> str:
    return moment.astimezone().strftime("%d.%m.%Y %H:%M")


def shown_code(code: str) -> str:
    return f"{code[:4]}-{code[4:]}" if len(code) == 8 else code


def first_code(code: str) -> str:
    return f"Код привязки WhatsApp Web: {shown_code(code)}. На телефоне: {LINK_PATH}, ввести код."


def renewed_code(code: str) -> str:
    return (
        f"WhatsApp Web обновил код привязки: {shown_code(code)} — прежний больше не действует. "
        f"Путь тот же: {LINK_PATH}."
    )


def not_linked_in_window(window_minutes: int, retry_after: datetime) -> str:
    return (
        f"WhatsApp Web не привязался за {window_minutes} мин. Следующая попытка — не раньше "
        f"{owner_time(retry_after)} или по POST /v1/link сервиса."
    )


def attempt_broken(reason: str, retry_after: datetime) -> str:
    return (
        f"Перепривязка WhatsApp Web сорвалась: {reason} Следующая попытка — не раньше "
        f"{owner_time(retry_after)} или по POST /v1/link сервиса."
    )


def not_linked_code_sent(sent_at: datetime) -> str:
    return (
        f"WhatsApp Web не привязан: код отправлен в Telegram {owner_time(sent_at)}. "
        f"Ввести его на телефоне: {LINK_PATH}."
    )


def not_linked_cooldown(retry_after: datetime) -> str:
    return (
        "WhatsApp Web не привязан: код не ввели вовремя, следующая попытка перепривязки — "
        f"не раньше {owner_time(retry_after)}."
    )
