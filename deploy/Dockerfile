FROM python:3.13-slim

RUN apt-get update && apt-get install -y --no-install-recommends curl jq git openssh-client xz-utils && rm -rf /var/lib/apt/lists/* && \
    curl -fsSL https://github.com/typst/typst/releases/latest/download/typst-x86_64-unknown-linux-musl.tar.xz | tar -xJ --strip-components=1 -C /usr/local/bin

WORKDIR /app

# Copy only pyproject.toml (not uv.lock - it may contain local editable paths)
COPY pyproject.toml ./

# Extract dependencies from pyproject.toml and install via pip
# This ignores [tool.uv.sources] and uses PyPI directly
RUN python -c "import tomllib; print('\n'.join(tomllib.load(open('pyproject.toml','rb'))['project']['dependencies']))" > requirements.txt && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY workers/ ./workers/
COPY data/ ./data/

ENV PYTHONPATH=/app

ARG APP_USER=sumarokov
RUN useradd --create-home --home-dir /home/${APP_USER} --uid 1000 ${APP_USER}
USER ${APP_USER}

RUN mkdir -p /home/${APP_USER}/.ssh && chmod 700 /home/${APP_USER}/.ssh && \
    printf "Host github-obsidian\n  HostName github.com\n  User git\n  IdentityFile ~/.ssh/personal_assistant\n  StrictHostKeyChecking accept-new\n" > /home/${APP_USER}/.ssh/config && \
    chmod 600 /home/${APP_USER}/.ssh/config

CMD ["python", "-m", "workers.bot"]
