#!/usr/bin/env python3
"""
Deploy script for personal_assistant bot.
Local deployment: docker compose build + down + up -d
"""
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[4]
COMPOSE_FILE = PROJECT_ROOT / "deploy" / "docker-compose.yml"


def run(cmd: list[str], description: str) -> None:
    print(f"\n--- {description} ---")
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    if result.returncode != 0:
        print(f"ERROR: '{' '.join(cmd)}' failed with exit code {result.returncode}")
        sys.exit(result.returncode)


def main() -> None:
    compose = ["docker", "compose", "-f", str(COMPOSE_FILE)]

    run(compose + ["build"], "Building Docker image")
    run(compose + ["down"], "Stopping containers")
    run(compose + ["up", "-d"], "Starting containers")

    print("\n--- Logs (last 20 lines) ---")
    subprocess.run(compose + ["logs", "--tail=20"], cwd=PROJECT_ROOT)

    print("\nDeploy completed.")


if __name__ == "__main__":
    main()
