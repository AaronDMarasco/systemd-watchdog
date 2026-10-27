.PHONY: build check lint clean help install pypi-deploy test uninstall
.SILENT: build check help install pypi-deploy test uninstall

define HELP

Targets:

  - build      - builds the 'wheel' distribution file (calls clean)
  - lint       - run formatters and linters
  - clean      - cleans temporary files
  - install    - builds and locally installs to your interpreter (calls uninstall and build)
  - uninstall  - removes locally installed copy
  - test       - runs unit tests

endef

export HELP
help:
	echo "$${HELP}"
	false

build: tool_check clean
	uv run poetry build --clean -vv

check: lint

lint: tool_check
	uv --preview-features format format --version "0.17.3"
	uv run ssort --check --diff
	uv run ruff check .
	uv run mypy .
	uv run pyrefly check --summarize-errors

clean:
	rm -rf build dist *.egg-info __pycache__

install: build uninstall
	uv pip install ./dist/*.whl

uninstall:
	-uv pip uninstall systemd_watchdog

test:
	uv run pytest -vv --cov --cov-report=html --cov-report=term-missing

pypi-deploy: lint build test
	# if this fails, need to put API key into poetry:
	# poetry config pypi-token.pypi pypi-XXX
	uv run poetry publish

.PHONY: tool_check
.SILENT: tool_check
tool_check:
	uv sync
