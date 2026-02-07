FROM python:3.13-slim

RUN apt-get update && apt-get install -y --no-install-recommends curl jq && rm -rf /var/lib/apt/lists/*

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

RUN useradd --create-home --home-dir /home/sumarokov --uid 1000 botuser
USER botuser

CMD ["python", "-m", "workers.bot"]
