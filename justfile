default:
    @just --list

clean:
    @echo "Cleaning cogency-cc..."
    @rm -rf dist build .pytest_cache .ruff_cache __pycache__ .venv
    @find . -type d -name "__pycache__" -exec rm -rf {} +

install:
    @poetry lock --no-cache
    @poetry install

ci:
    @poetry run ruff format .
    @poetry run ruff check . --fix --unsafe-fixes
    @poetry run pytest tests -q
    @poetry build

test:
    @poetry run pytest tests

format:
    @poetry run ruff format .

lint:
    @poetry run ruff check . --ignore F841

fix:
    @poetry run ruff check . --fix --unsafe-fixes

build:
    @poetry build

commits:
    @git --no-pager log --pretty=format:"%h | %ar | %s"
