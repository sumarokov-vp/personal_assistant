from typing import Literal

# Источники, которые пишет бот (case_add_event, задачи)
CaseSource = Literal[
    "owner", "assistant", "gmail", "whatsapp", "telegram", "todoist", "dropbox", "wiki"
]

# Источники, которые бот читает из ленты: кроме своих — события, записанные другими сервисами
# (scheduler — сервис расписаний assistant_scheduler). Сам бот от их имени не пишет
RecordedSource = CaseSource | Literal["scheduler"]
