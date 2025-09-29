.PHONY: sync
sync:
	uv sync --all-extras --group dev

# Linter and Formatter
.PHONY: format
format:
	uv run ruff format .

.PHONY: format-check
format-check:
	uv run ruff format --check .

.PHONY: lint
lint:
	uv run ruff check . --fix

.PHONY: lint-check
lint-check:
	uv run ruff check .

# Tests
.PHONY: test
test:
	uv run pytest tests/ -v

.PHONY: test-coverage
test-coverage:
	uv run pytest tests/ --cov=. --cov-report=html --cov-report=term

# ETL
.PHONY: etl
etl:
	uv run mcp-registry-etl

# Run servers
.PHONY: api
api:
	uv run uvicorn mcp_registry_search.api:app --reload

.PHONY: mcp
mcp:
	uv run mcp-registry-server

# Clean
.PHONY: clean
clean:
	rm -rf __pycache__ .pytest_cache .coverage htmlcov .ruff_cache
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete