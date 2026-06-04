# PMO Tool App Web — common tasks (requires uv: https://github.com/astral-sh/uv)
#
#   make install              Install Python deps
#   make build                Build docs/index.html from pmotools-app
#   make serve                Serve docs/ locally (PORT=8000 by default)
#   make stlite-check         Preview pin/CDN updates (dry run)
#   make stlite-sync STLITE_VERSION=1.3.0
#   make stlite-upgrade STLITE_VERSION=1.3.0   # sync pins + build
#   make stlite-latest        # sync to latest @stlite/browser on npm + build

.PHONY: help install build serve stlite-check stlite-sync stlite-upgrade stlite-latest submodule-update rebuild

UV ?= uv
PYTHON := $(UV) run python
PORT ?= 8000

help:
	@echo "PMO Tool App Web"
	@echo ""
	@echo "  make install                         uv sync"
	@echo "  make build                           generate docs/index.html"
	@echo "  make serve                           serve docs/ on PORT=$(PORT)"
	@echo "  make rebuild                         alias for build"
	@echo "  make submodule-update                update pmotools-app submodule"
	@echo ""
	@echo "Stlite / Pyodide (deps from pmotools-app/pyproject.toml):"
	@echo "  make stlite-check                    dry-run using current pins"
	@echo "  make stlite-check STLITE_VERSION=1.3.0"
	@echo "  make stlite-sync STLITE_VERSION=1.3.0"
	@echo "  make stlite-upgrade STLITE_VERSION=1.3.0   sync + build"
	@echo "  make stlite-latest                   npm latest @stlite/browser + build"

install:
	$(UV) sync

build:
	$(PYTHON) build_site.py

rebuild: build

serve:
	$(PYTHON) simple_server.py docs $(PORT)

submodule-update:
	git submodule update --init --remote pmotools-app

# --- @stlite/browser upgrades ---

stlite-check:
ifdef STLITE_VERSION
	$(PYTHON) scripts/sync_stlite_pins.py $(STLITE_VERSION) --dry-run
else
	$(PYTHON) scripts/sync_stlite_pins.py --dry-run
endif

stlite-sync:
ifndef STLITE_VERSION
	$(error Set STLITE_VERSION, e.g. make stlite-sync STLITE_VERSION=1.3.0)
endif
	$(PYTHON) scripts/sync_stlite_pins.py $(STLITE_VERSION)

stlite-upgrade:
ifndef STLITE_VERSION
	$(error Set STLITE_VERSION, e.g. make stlite-upgrade STLITE_VERSION=1.3.0)
endif
	$(PYTHON) scripts/sync_stlite_pins.py $(STLITE_VERSION) --build

stlite-latest:
	$(PYTHON) scripts/sync_stlite_pins.py latest --build
