# Everyday commands. Run `make` to list them.
.DEFAULT_GOAL := help

.PHONY: help setup dev db-up db-down migrate migration test lint format typecheck api-types build check

help: ## List the commands
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "} {printf "  make %-10s %s\n", $$1, $$2}'

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

migrate: db-up ## Apply database migrations
	cd backend && uv run alembic upgrade head

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
