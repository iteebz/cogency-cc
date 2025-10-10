default:
    @just --list

clean:
    @rm -rf dist build .pytest_cache .ruff_cache __pycache__ .venv
    @find . -type d -name "__pycache__" -exec rm -rf {} +

install:
    @poetry lock
    @poetry install

reload:
    @poetry remove cogency
    @poetry install ../cogency

ci: format fix test build

test:
    @PYTHONPATH=src:/Users/teebz/dev/space/public/cogency/src poetry run python -m pytest tests -v

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
