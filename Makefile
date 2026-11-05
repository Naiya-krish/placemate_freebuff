SHELL := /bin/bash
COMPOSE := docker compose
BACKEND := cd backend && PYTHONPATH=. ../.venv/bin/python
VENV := .venv
PY := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

.PHONY: help install install-backend install-frontend dev dev-local stop logs build \
	test test-backend test-frontend test-e2e lint lint-backend lint-frontend typecheck \
	migrate migration seed seed-questions fmt docker-reset

help:
	@echo "PlaceMate — make targets"
	@echo "  make dev            Start web, api, worker, postgres(pgvector), redis, minio via docker compose"
	@echo "  make dev-local      Run api + web locally (requires Postgres/Redis or DATABASE_URL sqlite)"
	@echo "  make install        Install backend venv + frontend node_modules"
	@echo "  make test           Backend pytest + frontend vitest"
	@echo "  make test-e2e       Playwright interview flow (starts servers)"
	@echo "  make lint           ruff + mypy + eslint + prettier check"
	@echo "  make migrate        Alembic upgrade head (docker compose)"
	@echo "  make seed           Idempotent demo seed (docker compose)"
	@echo "  make stop           Stop containers"

install: install-backend install-frontend

install-backend:
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r backend/requirements.txt

install-frontend:
	cd frontend && npm ci

dev:
	$(COMPOSE) up --build

dev-local:
	@echo "Starting API (:8000) and web (:3000). Use 'make stop' or Ctrl-C."
	@$(MAKE) -j2 api-local web-local

api-local:
	cd backend && PYTHONPATH=. ../$(VENV)/bin/uvicorn app.main:app --reload --port 8000

web-local:
	cd frontend && npm run dev

stop:
	$(COMPOSE) down --remove-orphans

logs:
	$(COMPOSE) logs -f --tail=120 api web worker

build:
	$(COMPOSE) build

migrate:
	$(COMPOSE) run --rm api alembic upgrade head

migration:
	@read -p "Migration message: " msg; \
	$(COMPOSE) run --rm api alembic revision --autogenerate -m "$$msg"

seed:
	$(COMPOSE) run --rm api python /app/scripts/seed_demo_data.py

seed-questions:
	$(COMPOSE) run --rm api python /app/scripts/seed_questions.py

test: test-backend test-frontend

test-backend:
	cd backend && PYTHONPATH=. ../$(VENV)/bin/pytest -q

test-frontend:
	cd frontend && npm run test -- --run

test-e2e:
	cd frontend && npm run test:e2e

lint: lint-backend lint-frontend

lint-backend:
	cd backend && ../$(VENV)/bin/ruff check . && ../$(VENV)/bin/ruff format --check .
	cd backend && ../$(VENV)/bin/mypy app

lint-frontend:
	cd frontend && npm run lint && npm run format:check

typecheck:
	cd frontend && npm run typecheck

fmt:
	cd backend && ../$(VENV)/bin/ruff check --fix . && ../$(VENV)/bin/ruff format .
	cd frontend && npm run format

docker-reset:
	$(COMPOSE) down -v --remove-orphans
