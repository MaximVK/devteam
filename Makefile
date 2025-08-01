.PHONY: help install test test-unit test-integration test-coverage lint format clean run-backend run-frontend setup

help:
	@echo "Available commands:"
	@echo "  make install          - Install all dependencies"
	@echo "  make test             - Run all tests"
	@echo "  make test-unit        - Run unit tests only"
	@echo "  make test-integration - Run integration tests only"
	@echo "  make test-coverage    - Run tests with coverage report"
	@echo "  make lint             - Run linters"
	@echo "  make format           - Format code"
	@echo "  make clean            - Clean up generated files"
	@echo "  make setup            - Run setup script"
	@echo "  make run-backend      - Start backend server"
	@echo "  make run-frontend     - Start frontend server"

install:
	poetry install
	cd web/frontend && npm install

test:
	poetry run pytest

test-unit:
	poetry run pytest tests/unit -v -m "not integration"

test-integration:
	poetry run pytest tests/integration -v -m integration

test-coverage:
	poetry run pytest --cov --cov-report=html --cov-report=term

lint:
	poetry run ruff check .
	poetry run mypy . --ignore-missing-imports

format:
	poetry run ruff format .
	poetry run black .

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf htmlcov
	rm -rf .ruff_cache
	rm -rf .mypy_cache
	rm -rf web/frontend/node_modules
	rm -rf web/frontend/dist

setup:
	python scripts/setup.py

run-backend:
	poetry run uvicorn web.backend:app --reload --port 8000

run-frontend:
	cd web/frontend && npm run dev