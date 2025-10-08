default:
    @just --list

clean:
    @rm -rf dist build .pytest_cache .ruff_cache __pycache__ .venv
    @find . -type d -name "__pycache__" -exec rm -rf {} +

install:
    @poetry install

ci: format fix test build

test:
    @PYTHONPATH=src poetry run python -m pytest tests -v

format:
    @poetry run ruff format .

lint:
    @poetry run ruff check . --ignore F841

fix:
    @poetry run ruff check . --fix --unsafe-fixes

build:
    @poetry build