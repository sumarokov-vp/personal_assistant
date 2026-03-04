#!/usr/bin/env python3
import subprocess
import sys
from logging import basicConfig, getLogger
from pathlib import Path

logger = getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[4]
COMPOSE_FILE = PROJECT_ROOT / "deploy" / "docker-compose.yml"


def run(cmd: list[str], description: str) -> None:
    logger.info("--- %s ---", description)
    result = subprocess.run(cmd, cwd=PROJECT_ROOT, check=False)  # noqa: S603
    if result.returncode != 0:
        logger.error("'%s' failed with exit code %d", " ".join(cmd), result.returncode)
        sys.exit(result.returncode)


def main() -> None:
    basicConfig(level="INFO")
    compose = ["docker", "compose", "-f", str(COMPOSE_FILE)]

    run(compose + ["build"], "Building Docker image")
    run(compose + ["down"], "Stopping containers")
    run(compose + ["up", "-d"], "Starting containers")

    logger.info("--- Logs (last 20 lines) ---")
    subprocess.run(compose + ["logs", "--tail=20"], cwd=PROJECT_ROOT, check=False)  # noqa: S603

    logger.info("Deploy completed.")


if __name__ == "__main__":
    main()
