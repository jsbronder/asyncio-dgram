# Passed to pytest -k and used to select only tests which match the given
# substring expression
UT ?=

# Run uv offline by default
OFFLINE ?= 1

SHELL = /usr/bin/env bash
PYTHON := $(shell which python3)
PACKAGE := $(shell $(PYTHON) setup.py --name | tr '-' '_')

# List of files in the repository
TEST_FILES := $(shell find test -type f -name '*.py')
PKG_FILES := $(shell find $(PACKAGE) -type f -name '*.py')
BIN_FILES := $(wildcard bin/*)

# Inferred targets from file names
LINT_TARGETS := setup.py $(PKG_FILES) $(BIN_FILES) $(TEST_FILES)
TEST_TARGETS := $(TEST_FILES:test/test_%.py=test_%)

UV := uv --no-progress
ifeq ($(OFFLINE), 1)
	UV := $(UV) --offline
endif

.PHONY: \
	$(TEST_TARGETS) \
	sync \
	format \
	lint \
	type-check \
	test

default:

# Purposely ignoring $(OFFLINE) here
sync:
	@uv sync --frozen

check-format:
	@$(UV) run black --check $(LINT_TARGETS)
format:
	@$(UV) run black $(LINT_TARGETS)
lint:
	@$(UV) run flake8 --filename='*' $(LINT_TARGETS)
type-check:
	@$(UV) run mypy $(PACKAGE) test/  example.py
test:
	@$(UV) run pytest --log-level=DEBUG -W default -v -s
$(TEST_TARGETS):
	@$(UV) run pytest --log-cli-level=DEBUG -W default -v -s test/$(@).py $(if $(UT),-k $(UT),)
