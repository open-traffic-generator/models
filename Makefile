# Rebuilds the generated artifacts only when a schema source (or build.py)
# is newer than the last build. `build.py` regenerates every artifact in
# one run, so artifacts/openapi.yaml serves as the sentinel for all of them.
# The venv is created/updated on demand, keyed off requirements.txt.

VENV := .venv
PYTHON := $(VENV)/bin/python
VENV_SENTINEL := $(VENV)/.deps-installed

# All schema sources: every yaml file except generated/vendored content.
SOURCES := $(shell find . -name '*.yaml' \
	-not -path './.venv/*' \
	-not -path './artifacts/*') build.py

SENTINEL := artifacts/openapi.yaml

.PHONY: build venv clean clean-venv

build: $(SENTINEL)

$(SENTINEL): $(VENV_SENTINEL) $(SOURCES)
	$(PYTHON) build.py

venv: $(VENV_SENTINEL)

$(VENV_SENTINEL): requirements.txt
	python3 -m venv $(VENV)
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r requirements.txt
	touch $(VENV_SENTINEL)

clean:
	rm -rf artifacts

clean-venv:
	rm -rf $(VENV)
