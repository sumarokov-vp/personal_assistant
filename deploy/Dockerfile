# Образ бота для colima на Mac mini (linux/arm64). Зависимости ставятся uv строго по uv.lock.
#
# Движок — ClaudeSdkProvider ai_framework: claude-agent-sdk везёт CLI Claude Code бинарём внутри
# колеса (claude_agent_sdk/_bundled/claude), Node не нужен. CLI ходит по подписке
# (CLAUDE_CODE_OAUTH_TOKEN из окружения) и пишет сессии в $HOME/.claude — домашний каталог uid 1000.
# Встроенные инструменты CLI выключены managed settings в /etc/claude-code: файл root-овый,
# грузится всегда, независимо от setting_sources, и пользователь контейнера его не перепишет.
#
# Двухэтапная сборка: в builder git нужен, чтобы uv склонировал ai-bot-framework (git-зависимость
# по тегу, tool.uv.sources в pyproject.toml). В итоговом образе git и openssh-client нужны вики:
# бот клонирует obsidian_wiki по WIKI_REMOTE_URL (ssh) в том WIKI_DIR и пушит правки deploy-ключом.
# Ключи хоста github.com — из deploy/ssh/known_hosts (сверены с опубликованными отпечатками GitHub),
# кладутся системным known_hosts: accept-new в GitCli на них уже не срабатывает.
FROM python:3.13-slim AS builder

RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

FROM python:3.13-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates git openssh-client \
    && rm -rf /var/lib/apt/lists/*

COPY deploy/ssh/known_hosts /etc/ssh/ssh_known_hosts

ENV PYTHONPATH=/app \
    PATH=/app/.venv/bin:$PATH \
    ENABLE_CLAUDEAI_MCP_SERVERS=false \
    DISABLE_AUTOUPDATER=1 \
    CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1

COPY deploy/claude-code/managed-settings.json /etc/claude-code/managed-settings.json

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY pyproject.toml uv.lock ./
COPY src/ ./src/
COPY workers/ ./workers/
COPY data/ ./data/

ARG APP_USER=sumarokov
ARG APP_UID=1000
RUN useradd --create-home --home-dir /home/${APP_USER} --uid ${APP_UID} ${APP_USER} \
    && mkdir -p /wiki \
    && chown ${APP_UID} /wiki
# Том вики смонтирован с хоста (virtiofs colima): владелец каталогов в контейнере не обязательно
# uid 1000, и git без safe.directory отказался бы работать с копией. Путь — WIKI_DIR из compose.yaml.
RUN git config --system --add safe.directory /wiki/obsidian_wiki
USER ${APP_USER}

CMD ["python", "-m", "workers.bot"]
