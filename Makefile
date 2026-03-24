.PHONY: help build run dry-run resume list-regions test lint clean shell

ENV_FILE := .env

check-env:
	@test -f $(ENV_FILE) || (echo "\nERROR: .env not found.\nRun: cp .env.example .env and add your GOOGLE_MAPS_API_KEY\n" && exit 1)

help:
	@echo ""
	@echo "daleel — Saudi Arabia Business Directory Scraper"
	@echo "================================================="
	@echo "  build          Build Docker image"
	@echo "  run            Run scraper (use ARGS for CLI args)"
	@echo "  dry-run        Cost estimate only (no API calls)"
	@echo "  resume         Resume last interrupted run"
	@echo "  list-regions   Show available regions and cities"
	@echo "  shell          Open a bash shell in the container"
	@echo "  test           Run test suite"
	@echo "  lint           Run ruff linter"
	@echo "  clean          Remove data and cache files"
	@echo ""
	@echo "Examples:"
	@echo "  make run ARGS='--region Riyadh --target 5000'"
	@echo "  make dry-run ARGS='--region Riyadh --target 5000'"
	@echo ""

build:
	docker compose build

run: check-env
	docker compose run --rm daleel $(ARGS)

dry-run: check-env
	docker compose run --rm daleel $(ARGS) --dry-run

resume: check-env
	docker compose run --rm daleel --resume

list-regions:
	docker compose run --rm daleel --list-regions

shell:
	docker compose run --rm --entrypoint bash daleel

test:
	docker compose run --rm --entrypoint bash daleel -c "PYTHONPATH=/app/src pytest tests/ -v"

lint:
	docker compose run --rm --entrypoint bash daleel -c "ruff check src/ tests/"

clean:
	rm -rf data/checkpoints/* data/raw/*
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
