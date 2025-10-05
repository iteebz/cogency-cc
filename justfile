default *ARGS:
    @poetry run python -m src.cc {{ARGS}}

install:
    @poetry install

dev-setup: install
    @poetry run cc-setup

reload:
    @poetry remove cogency && poetry add ../cogency

test:
    @poetry run python -m pytest tests -v

cov:
    @poetry run pytest --cov=src/cogency_code tests/

format:
    @poetry run ruff format .

lint:
    @poetry run ruff check .

fix:
    @poetry run ruff check . --fix --unsafe-fixes

build:
    @poetry build

publish: ci build
    @poetry publish

clean:
    @rm -rf dist build .pytest_cache .ruff_cache __pycache__ .venv
    @find . -type d -name "__pycache__" -exec rm -rf {} +

commits:
    @git --no-pager log --pretty=format:"%ar %s"

ci: format fix test build