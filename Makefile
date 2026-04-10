.PHONY: dev dev-backend dev-frontend test test-backend test-frontend lint install

# Development
dev:
	docker compose up

dev-backend:
	cd backend && uvicorn app.main:app --reload --port 8000

dev-frontend:
	cd frontend && npm run dev

# Testing
test: test-backend test-frontend

test-backend:
	cd backend && python -m pytest -n auto --cov=app --cov-fail-under=70 -v

test-frontend:
	cd frontend && npx vitest run --coverage

# Linting
lint: lint-backend lint-frontend

lint-backend:
	cd backend && ruff check . && ruff format --check .

lint-frontend:
	cd frontend && npx eslint src/ && npx tsc --noEmit

# Install
install:
	cd backend && pip install -e ".[dev]"
	cd frontend && npm install
