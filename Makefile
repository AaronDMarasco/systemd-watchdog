.PHONY: build lint clean help install pypi-deploy test uninstall
.SILENT: build lint help install pypi-deploy test uninstall

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

build: poetry_check clean
	poetry build --clean -vv

lint: tool_check
	echo Poetry:
	poetry check
	echo Black:
	find -name '*.py' | xargs black
	echo Ruff:
	find -name '*.py' | xargs ruff check --output-format=concise
	echo MyPy:
	find -name '*.py' | xargs mypy

clean:
	rm -rf build dist *.egg-info __pycache__

install: build uninstall
	pip3 install --user ./dist/*.whl

uninstall:
	-pip3 uninstall -y systemd_watchdog

test:
	./test_systemd_watchdog.py

pypi-deploy: lint build test
	# if this fails, need to put API key into poetry:
	# poetry config pypi-token.pypi pypi-XXX
	poetry publish

.PHONY: tool_check
.SILENT: tool_check
tool_check: poetry_check
	for t in black mypy ruff; do pip3 list | egrep "^$${t}\s" >/dev/null || (echo "Need to ' pip3 install $${t} '" && false); done

.PHONY: poetry_check
.SILENT: poetry_check

POETRY_INSTALLED = $(shell pip3 list | egrep '^poetry\s')
poetry_check:
ifeq ($(POETRY_INSTALLED),)
  $(error Need to ' pip3 install "poetry>=2" ')
endif
	true
