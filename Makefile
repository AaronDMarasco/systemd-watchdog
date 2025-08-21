.PHONY: build clean help install pypi-deploy test uninstall
.SILENT: help install pypi-deploy test uninstall

define HELP

Targets:

  - build      - builds the 'wheel' distribution file (calls clean)
  - check      - run linters
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

check: black_check ruff_check
	true

clean:
	rm -rf build dist *.egg-info __pycache__

install: build uninstall
	pip3 install --user ./dist/*.whl

uninstall:
	-pip3 uninstall -y systemd_watchdog

test:
	./test_systemd_watchdog.py

pypi-deploy: build test ~/.pypirc
	twine upload --repository pypi dist/*

.PHONY: black_check poetry_check ruff_check
.SILENT: black_check poetry_check ruff_check
BLACK_INSTALLED = $(shell pip3 list | egrep '^black\s')
black_check:
ifeq ($(BLACK_INSTALLED),)
  $(error Need to ' pip3 install black ')
endif
	true

POETRY_INSTALLED = $(shell pip3 list | egrep '^poetry\s')
poetry_check:
ifeq ($(POETRY_INSTALLED),)
  $(error Need to ' pip3 install "poetry>=2" ')
endif
	true

RUFF_INSTALLED = $(shell pip3 list | egrep '^ruff\s')
ruff_check:
ifeq ($(RUFF_INSTALLED),)
  $(error Need to ' pip3 install ruff ')
endif
	true
