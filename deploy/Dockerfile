# Образ бота для colima на Mac mini (linux/arm64). Зависимости ставятся uv строго по uv.lock.
FROM python:3.13-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl git jq xz-utils \
    && rm -rf /var/lib/apt/lists/* \
    && curl -fsSL "https://github.com/typst/typst/releases/latest/download/typst-$(uname -m)-unknown-linux-musl.tar.xz" \
       | tar -xJ --strip-components=1 -C /usr/local/bin \
    && typst --version

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONPATH=/app \
    PATH=/app/.venv/bin:$PATH

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY src/ ./src/
COPY workers/ ./workers/
COPY data/ ./data/

ARG APP_USER=sumarokov
ARG APP_UID=1000
RUN useradd --create-home --home-dir /home/${APP_USER} --uid ${APP_UID} ${APP_USER} \
    && mkdir -p /app/workspace /home/${APP_USER}/.claude \
    && chown ${APP_USER}:${APP_USER} /app/workspace /home/${APP_USER}/.claude
USER ${APP_USER}

CMD ["python", "-m", "workers.bot"]
