# Everyday commands. Run `make` to list them.
.DEFAULT_GOAL := help

.PHONY: help setup dev db-up db-down migrate seed demo catalog eval-stylist golden migration test lint format typecheck api-types build check audit housekeeping e2e trend-scout weekly-digest

help: ## List the commands
	@grep -E '^[a-z0-9-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "} {printf "  make %-10s %s\n", $$1, $$2}'

setup: ## Install dependencies and create .env from .env.example
	@test -f .env || (cp .env.example .env && echo "Created .env from .env.example")
	cd backend && uv sync
	cd frontend && pnpm install

dev: migrate ## Run the API on :8000 and the web app on :3000 (Ctrl+C stops both)
	@trap 'kill 0' EXIT; \
	(cd backend && uv run uvicorn app.main:app --reload --port 8000) & \
	(cd frontend && pnpm dev) & \
	wait

db-up: ## Start the local Postgres container
	docker compose up -d --wait db

db-down: ## Stop the local Postgres container (the data is kept)
	docker compose down

migrate: db-up ## Apply database migrations, then load the reference data in seed/
	cd backend && uv run alembic upgrade head
	cd backend && uv run python -m scripts.agent_setup
	cd backend && uv run python -m scripts.seed_reference

seed: db-up ## Load the reference data in seed/ (safe to run again)
	cd backend && uv run python -m scripts.seed_reference

demo: migrate ## Fill the demo account (demo@example.com) with a wardrobe of generic staples
	cd backend && uv run python -m scripts.load_demo

catalog: migrate ## Load a demo catalogue (check the dataset's licence first): make catalog file=styles.csv
	@test -n "$(file)" || (echo 'Usage: make catalog file=path/to/styles.csv' && exit 1)
	cd backend && uv run python -m scripts.load_catalog --file "$(abspath $(file))"

eval-stylist: ## Ask the stylist the evaluation questions with the real model (costs a few cents)
	cd backend && uv run python -m scripts.eval_stylist

golden: ## Export a wardrobe for golden-set labelling: make golden email=you@example.com
	@test -n "$(email)" || (echo 'Usage: make golden email=you@example.com' && exit 1)
	cd backend && uv run python -m scripts.export_golden --email "$(email)"

migration: db-up ## Create a migration from model changes: make migration m="add users"
	@test -n "$(m)" || (echo 'Usage: make migration m="what changed"' && exit 1)
	cd backend && uv run alembic revision --autogenerate -m "$(m)"

test: db-up ## Run the backend and frontend tests
	cd backend && uv run pytest
	cd frontend && pnpm test

lint: ## Check lint and formatting
	cd backend && uv run ruff check . && uv run ruff format --check .
	cd frontend && pnpm lint && pnpm format:check

format: ## Fix formatting and auto-fixable lint
	cd backend && uv run ruff format . && uv run ruff check --fix .
	cd frontend && pnpm format

typecheck: ## Run the type checkers
	cd backend && uv run mypy
	cd frontend && pnpm typecheck

api-types: ## Regenerate the frontend's API types after changing a route
	cd backend && uv run python -m scripts.export_openapi ../frontend/lib/api/openapi.json
	cd frontend && pnpm gen:api

build: ## Production build of the web app
	cd frontend && pnpm build

check: lint typecheck test build ## Everything CI runs

e2e: ## End-to-end tests in a browser, against a running app (make dev first; E2E_BASE_URL for another)
	cd frontend && pnpm e2e

housekeeping: db-up ## Remove what has expired: old demo accounts, unsaved photos, old error reports
	cd backend && uv run python -m scripts.housekeeping

audit: ## Check the packages the live app runs on for known vulnerabilities
	cd backend && uv export --format requirements-txt --no-dev --locked --no-emit-project | uvx pip-audit --disable-pip --no-deps -r /dev/stdin
	cd frontend && pnpm audit --prod

trend-scout: db-up ## Run the Trend Scout once on the local database (needs SEARCH_PROVIDER and AI_PROVIDER)
	cd backend && uv run python -m app.jobs.trend_scout

weekly-digest: db-up ## Send the weekly emails that are due today, on the local database (printed unless EMAIL_PROVIDER is set)
	cd backend && uv run python -m app.jobs.weekly_digest
