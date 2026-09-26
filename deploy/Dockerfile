# Образ бота для colima на Mac mini (linux/arm64). Зависимости ставятся uv строго по uv.lock.
#
# Движок — ClaudeSdkProvider ai_framework: claude-agent-sdk везёт CLI Claude Code бинарём внутри
# колеса (claude_agent_sdk/_bundled/claude), Node не нужен. CLI ходит по подписке
# (CLAUDE_CODE_OAUTH_TOKEN из окружения) и пишет сессии в $HOME/.claude — домашний каталог uid 1000.
# Встроенные инструменты CLI выключены managed settings в /etc/claude-code: файл root-овый,
# грузится всегда, независимо от setting_sources, и пользователь контейнера его не перепишет.
#
# Двухэтапная сборка: git нужен только чтобы uv склонировал ai-bot-framework (git-зависимость
# по тегу, tool.uv.sources в pyproject.toml) — в итоговом образе его быть не должно.
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
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

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
RUN useradd --create-home --home-dir /home/${APP_USER} --uid ${APP_UID} ${APP_USER}
USER ${APP_USER}

CMD ["python", "-m", "workers.bot"]
