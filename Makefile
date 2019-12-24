# Specify the location where the package is to be installed. Note that this is
# a required variable if the package is expected to be installed in an OE stage
# environment via 'eto stage install'
DESTDIR ?= /

# This argument is used when selecting a unit test by name.
UT ?=

# Define the shell to use within the Makefile
SHELL = /usr/bin/env bash

# Define a set of constants based upon the version of python used and metadata
PYTHON := $(shell which python3)
PACKAGE := $(shell $(PYTHON) setup.py --name | tr '-' '_')
VERSION := $(shell $(PYTHON) setup.py --version)

# List of files in the repository
TEST_FILES := $(wildcard test/test_*.py)
PKG_FILES := $(shell find $(PACKAGE) -type f -name '*.py')
REQ_FILES := $(wildcard requirements*.txt)
BIN_FILES := $(wildcard bin/*)

# Inferred targets from file names
LINT_TARGETS := setup.py $(PKG_FILES) $(BIN_FILES) $(shell find test -type f -name '*.py')
TEST_TARGETS := $(TEST_FILES:test/test_%.py=test_%)
EXT_TARGETS := $(wildcard ext/*)

.PHONY: \
	$(EXT_TARGETS) \
	$(REQ_FILES) \
	$(TEST_TARGETS) \
	clean \
	clean-build \
	clean-env \
	ext \
	format \
	install \
	lint \
	requirements \
	test

default:


clean: clean-build clean-env


ifndef VIRTUAL_ENV
clean-env:
	@rm -rf .venv*
	@rm -rf .dev*
endif


clean-build:
	@rm -rf .pytest_cache
	@rm -rf .eggs
	@rm -rf dist
	@rm -rf build
	@rm -rf $(PACKAGE).egg-info


ext: $(EXT_TARGETS)
$(EXT_TARGETS):
	$(MAKE) -C $@ install_noext


requirements: $(REQ_FILES)
$(REQ_FILES):
	@$(PYTHON) -m pip install --disable-pip-version-check -r $@


dist: dist/$(PACKAGE)-$(VERSION).tar.gz
dist/$(PACKAGE)-$(VERSION).tar.gz: $(PKG_FILES) setup.py
	$(PYTHON) setup.py sdist bdist_wheel


format:
	@black $(LINT_TARGETS)
lint:
	@flake8 --filename='*' $(LINT_TARGETS)


test:
	@$(PYTHON) -m pytest --log-level=DEBUG -W default -v -s
$(TEST_TARGETS):
	@$(PYTHON) -m pytest --log-cli-level=DEBUG -W default -v -s test/$(@).py $(if $(UT),-k $(UT),)


install:
	$(PYTHON) setup.py install --root $(DESTDIR) --prefix .


install_noext: dist
	$(PYTHON) -m pip install --no-deps \
		--upgrade --force-reinstall --no-index dist/$(PACKAGE)-$(VERSION).tar.gz
