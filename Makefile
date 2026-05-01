.PHONY: help install install-dev test test-cov lint format type clean run-all generate train route serve dashboard

help:
	@echo "Arbiter: Intelligent Request Router"
	@echo ""
	@echo "Available targets:"
	@echo "  make install         - Install dependencies with uv"
	@echo "  make install-dev     - Install with dev extras (testing, linting)"
	@echo "  make test            - Run test suite"
	@echo "  make test-cov        - Run tests with HTML coverage report"
	@echo "  make lint            - Lint with ruff"
	@echo "  make format          - Format and auto-fix with ruff"
	@echo "  make type            - Ruff check with type-related rules"
	@echo "  make clean           - Remove generated files and caches"
	@echo "  make generate        - Generate synthetic training data"
	@echo "  make train           - Train latency prediction model"
	@echo "  make route           - Run router simulation"
	@echo "  make serve           - Start Context Service (FastAPI on :8000)"
	@echo "  make dashboard       - Start Streamlit dashboard (requires service running)"
	@echo "  make run-all         - Full pipeline: data → train → route"
	@echo ""

install:
	uv sync

install-dev:
	uv sync --all-extras --all-groups

test:
	uv run pytest

test-cov:
	uv run pytest --cov-report=html --cov-report=term-missing
	@echo "Coverage report: htmlcov/index.html"

lint:
	uv run ruff check arbiter/ data/ tests/

format:
	uv run ruff format arbiter/ data/ tests/
	uv run ruff check --fix arbiter/ data/ tests/

type:
	uv run ruff check --select ANN,TCH arbiter/ data/ tests/ || true

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete
	find . -type d -name '*.egg-info' -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name '.pytest_cache' -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name '.ruff_cache' -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name 'htmlcov' -exec rm -rf {} + 2>/dev/null || true
	rm -f .coverage
	@echo "Cleaned cache and temp files"

generate:
	uv run python data/generate.py

train:
	uv run python -m arbiter.routing.model

route:
	uv run python -m arbiter.routing.engine

serve:
	uv run uvicorn arbiter.context.api:app --reload

dashboard:
	uv run streamlit run arbiter/observability/dashboard.py

run-all: clean generate train route
	@echo ""
	@echo "Pipeline complete! (data generation, model training, routing simulation)"
	@echo ""
	@echo "Next steps:"
	@echo "  Terminal 1: make serve        # Start Context Service"
	@echo "  Terminal 2: make dashboard    # Start dashboard (after service is up)"
	@echo "  Terminal 3: make test         # Run test suite"
	@echo ""

.DEFAULT_GOAL := help
