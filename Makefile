.PHONY: help install test lint format type-check security ci clean

help:  ## Show this help message
	@echo "================================"
	@echo "🛩️  Flight Pipeline Make Commands"
	@echo "================================"
	@echo ""
	@echo "Development:"
	@echo "  make install       Install all dependencies"
	@echo "  make clean         Clean artifacts (cache, logs)"
	@echo ""
	@echo "Testing:"
	@echo "  make test          Run all unit tests"
	@echo "  make test-unit     Run unit tests (fast)"
	@echo "  make test-cov      Run tests with coverage report"
	@echo "  make test-coverage Generate HTML coverage report"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint          Run ruff linter"
	@echo "  make format        Auto-format code with black"
	@echo "  make format-check  Check formatting without changes"
	@echo "  make type-check    Run mypy type checker"
	@echo ""
	@echo "Security:"
	@echo "  make security      Run security scans (bandit, safety)"
	@echo ""
	@echo "Pipeline:"
	@echo "  make producer      Start flight producer (requires Kafka)"
	@echo "  make orchestrator  Start full streaming orchestrator"
	@echo "  make dashboard     Show analytics dashboard"
	@echo "  make status        Check system status"
	@echo ""
	@echo "CI/CD:"
	@echo "  make ci-local      Run all checks locally (what CI runs)"
	@echo ""
	@echo "================================"

install:  ## Install all dependencies
	pip install --upgrade pip
	pip install -r requirements.txt
	pip install -r requirements-dev.txt
	pre-commit install
	@echo "✅ Dependencies installed. Run 'make help' for commands."

test:  ## Run all unit tests
	pytest tests/unit/ -v

test-unit:  ## Run unit tests (short output)
	pytest tests/unit/

test-cov:  ## Run tests with coverage summary
	pytest tests/unit/ --cov=. --cov-report=term --cov-report=html

test-coverage:  ## Generate and open HTML coverage report
	pytest tests/unit/ --cov=. --cov-report=html
	@echo "📊 Coverage report generated in htmlcov/index.html"
	@echo "   Open htmlcov/index.html in your browser"

lint:  ## Run ruff linter
	ruff check .

format:  ## Auto-format code with black
	black . --exclude venv

format-check:  ## Check formatting without changes
	black . --check --exclude venv

type-check:  ## Run mypy type checker
	mypy --ignore-missing-imports .

security:  ## Run security scans
	@echo "🔒 Running security scans..."
	bandit -r . -x tests,venv
	safety check

ci-local:  ## Run all checks locally (simulates CI)
	@echo "🚀 Running all checks (what CI runs)..."
	make lint
	make type-check
	make test
	make security
	@echo "✅ All checks passed!"

producer:  ## Start flight producer (Kafka must be running)
	@echo "🔄 Starting flight producer..."
	@echo "⚠️  Make sure Kafka is running: docker-compose up -d"
	python OpenSky/flight_producer.py

orchestrator:  ## Start full streaming orchestrator
	@echo "🚀 Starting flight streaming orchestrator..."
	python flight_streaming_orchestrator.py

dashboard:  ## Show analytics dashboard
	@echo "📊 Showing analytics dashboard..."
	@echo "⚠️  Make sure Snowflake is configured and data is loaded"
	python Faust/analytics_dashboard.py

status:  ## Check system status
	@echo "🔍 Checking system status..."
	python quick_status_check.py

clean:  ## Clean artifacts
	@echo "🧹 Cleaning artifacts..."
	rm -rf .pytest_cache htmlcov coverage.xml .coverage
	rm -rf Faust/__pycache__ OpenSky/__pycache__ tests/__pycache__
	rm -rf schemas/__pycache__ dagster_app/__pycache__
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete
	@echo "✅ Clean complete"

.DEFAULT_GOAL := help
