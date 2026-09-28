# whatsapp_web — хостовый сервис WhatsApp Web на Mac mini

Отдельный uv-проект: в образ бота, его mypy и import-linter не входит. Chromium под Playwright с
постоянным профилем (связанное устройство аккаунта владельца) достаёт документ чата, который сервер
WhatsApp уже удалил с CDN: открывает просмотр в WhatsApp Web, телефон владельца перезаливает файл.

- Слушает только `127.0.0.1:$WHATSAPP_WEB_PORT` (умолчание 18790), каждый запрос — с ключом
- Браузер поднимается при старте сервиса (проверка привязки) и по запросу, закрывается после
  `WHATSAPP_WEB_IDLE_SECONDS` простоя (600). Запросы к странице строго по одному
- В логах — только хеши чата и имени файла

## Окружение

| Переменная | Умолчание | Что |
|---|---|---|
| `WHATSAPP_WEB_KEY_FILE` | — (обязательна) | файл 0600, первая строка — ключ API |
| `WHATSAPP_WEB_PROFILE_DIR` | `~/docker/personal_assistant/whatsapp-web/profile` | профиль Chromium (0700) |
| `WHATSAPP_WEB_PORT` | `18790` | порт на 127.0.0.1 |
| `WHATSAPP_WEB_HEADLESS` | `1` | `0` — с окном |
| `WHATSAPP_WEB_IDLE_SECONDS` | `600` | простой до закрытия браузера |
| `WHATSAPP_WEB_REUPLOAD_SECONDS` | `120` | ожидание перезаливки файла телефоном |

Два Chromium на одном профиле не живут: пока сервис запущен, профиль не открывать ничем другим.

## Контракт

`POST /v1/documents/fetch`, `Authorization: Bearer <ключ>`, тело
`{"chat_title", "chat_jid", "file_name", "size", "sent_at"}` (обязательны `chat_jid`, `file_name`, `size`).
Чат ищется по `chat_title`, для личного чата — ещё по номеру из `chat_jid`. `file_name` из снимка
может быть без расширения — совпадает и с показанным `<имя>.<расширение>`. Одно имя у нескольких
документов — берётся тот, чей размер равен `size`.

- 200 — байты файла; `Content-Type` по показанному имени; `X-File-Name: UTF-8''<percent-encoded>` —
  имя, как его показывает WhatsApp Web (с расширением); `X-Elapsed-Ms`
- ошибки — `{"error": "<код>", "detail": "<по-русски>"}`: 401 `unauthorized`, 422 `bad_request`,
  404 `chat_not_found` / `document_not_found`, 409 `not_linked`, 502 `ui_changed` (шаг в detail),
  502 `size_mismatch`, 504 `reupload_timeout`, 500 `internal_error`

`GET /v1/health` (с ключом) → `{"linked": true, "checked_at": "…Z"}` — последнее известное
состояние привязки, браузер не поднимает; до первой проверки — проверяет.

## Команды

```
uv sync
uv run pytest && uv run ruff check . && uv run mypy src tests
WHATSAPP_WEB_KEY_FILE=... uv run python -m whatsapp_web
```
