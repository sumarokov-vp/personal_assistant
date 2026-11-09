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

# Typst для PDF по шаблону Smartist (ядро, protocol_make). Бинарь — релиз typst фиксированной
# версии со сверкой sha256, не apt: в Debian он старый и без пакетного менеджера @local.
# Шрифты — те, что называет @local/fonts (fonts-linux.typ): PT Sans с кириллицей, Noto Color
# Emoji, JetBrains Mono; typst находит их в /usr/share/fonts сам. Пакеты @local/smartist и
# @local/fonts лежат в репе (deploy/typst, источник и версия — deploy/typst/SOURCE.txt):
# сборка образа не ходит в чужую приватную репу.
ARG TYPST_VERSION=0.15.1
ARG TARGETARCH
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl xz-utils fonts-paratype fonts-noto-color-emoji fonts-jetbrains-mono \
    && case "${TARGETARCH:-arm64}" in \
        arm64) triple=aarch64-unknown-linux-musl; sum=5aa8d74a3d906e60ea12a66ac2f37f8eef1b14cbad7182a745e393a10c23dcee ;; \
        amd64) triple=x86_64-unknown-linux-musl; sum=a6d077d0a95eed5a2eba715b2dae06be954f624ccbf85758a03f389ded33118c ;; \
        *) echo "typst: нет сборки под ${TARGETARCH}" >&2; exit 1 ;; \
       esac \
    && curl -fsSL -o /tmp/typst.tar.xz \
        "https://github.com/typst/typst/releases/download/v${TYPST_VERSION}/typst-${triple}.tar.xz" \
    && echo "${sum}  /tmp/typst.tar.xz" | sha256sum -c - \
    && tar -xJf /tmp/typst.tar.xz -C /tmp \
    && install -m 0755 "/tmp/typst-${triple}/typst" /usr/local/bin/typst \
    && rm -rf /tmp/typst.tar.xz "/tmp/typst-${triple}" \
    && apt-get purge -y --auto-remove curl xz-utils \
    && rm -rf /var/lib/apt/lists/*

COPY deploy/typst/packages/ /usr/local/share/typst/packages/
COPY deploy/typst/smoke.typ /usr/local/share/typst/smoke.typ

ENV PYTHONPATH=/app \
    PATH=/app/.venv/bin:$PATH \
    ENABLE_CLAUDEAI_MCP_SERVERS=false \
    DISABLE_AUTOUPDATER=1 \
    CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1 \
    TYPST_PACKAGE_PATH=/usr/local/share/typst/packages

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
