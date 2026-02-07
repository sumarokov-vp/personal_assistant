#!/bin/bash
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

cd "$(dirname "$0")/.."

echo -e "${YELLOW}Running linters...${NC}"
uv run ruff check .
uv run mypy .
echo -e "${GREEN}Linters passed!${NC}"

echo -e "${YELLOW}Running tests...${NC}"
uv run pytest tests/ -v
echo -e "${GREEN}Tests passed!${NC}"

echo -e "${YELLOW}Stopping old container...${NC}"
docker compose -f deploy/docker-compose.yml down || true

echo -e "${YELLOW}Building image (no cache)...${NC}"
docker compose -f deploy/docker-compose.yml build

echo -e "${YELLOW}Starting new container...${NC}"
docker compose -f deploy/docker-compose.yml up -d

echo -e "${GREEN}Deploy completed!${NC}"
