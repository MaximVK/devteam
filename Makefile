.PHONY: help install test test-unit test-integration test-coverage lint format clean run-backend run-frontend setup start stop status logs

help:
	@echo "Available commands:"
	@echo ""
	@echo "🚀 Main Commands:"
	@echo "  make start            - Start all DevTeam services"
	@echo "  make stop             - Stop all DevTeam services"
	@echo "  make status           - Check status of all services"
	@echo "  make logs             - Tail all service logs"
	@echo "  make restart          - Restart all services"
	@echo "  make clean-logs       - Clean up log files"
	@echo ""
	@echo "📄 Log Commands:"
	@echo "  make logs-<service>   - Tail logs for specific service (e.g., logs-backend)"
	@echo "  make status-<service> - Check status of specific service"
	@echo ""
	@echo "🔧 Development Commands:"
	@echo "  make install          - Install all dependencies"
	@echo "  make test             - Run all tests"
	@echo "  make test-unit        - Run unit tests only"
	@echo "  make test-integration - Run integration tests only"
	@echo "  make test-coverage    - Run tests with coverage report"
	@echo "  make lint             - Run linters"
	@echo "  make format           - Format code"
	@echo "  make clean            - Clean up generated files"
	@echo "  make setup            - Run setup script"
	@echo "  make run-backend      - Start backend server only"
	@echo "  make run-frontend     - Start frontend server only"

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

# Main DevTeam commands
start:
	@echo "🚀 Starting DevTeam..."
	@./start.sh

stop:
	@echo "🛑 Stopping DevTeam..."
	@./stop.sh

status:
	@echo "🔍 Checking DevTeam status..."
	@python check_status.py

logs:
	@echo "📄 Tailing logs (Ctrl+C to exit)..."
	@tail -f logs/*.log

# Additional useful commands
restart: stop start
	@echo "♻️  DevTeam restarted"

clean-logs:
	@echo "🧹 Cleaning up log files..."
	@rm -rf logs/*.log
	@echo "✅ Logs cleaned"

# View logs for specific service (e.g., make logs-backend)
logs-%:
	@echo "📄 Tailing logs for $*..."
	@tail -f logs/$*.log

# Check status of specific service (e.g., make status-backend)
status-%:
	@echo "🔍 Checking $* status..."
	@ps aux | grep -v grep | grep -q "$*" && echo "✅ $* is running" || echo "❌ $* is not running"