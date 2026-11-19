# The one entry point for setup, running and the gate. See CLAUDE.md.
SHELL := /bin/bash
.DEFAULT_GOAL := check
.PHONY: setup dev check check-backend check-frontend format openapi

ROOT := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
NODE := $(ROOT)scripts/with-node.sh

setup:
	cd backend && uv sync --locked
	cd frontend && $(NODE) npm ci
	git config core.hooksPath .githooks
	@command -v gitleaks >/dev/null 2>&1 || echo "WARNING: gitleaks is not installed, so commits are NOT scanned for secrets. Install it: https://github.com/gitleaks/gitleaks"

# Backend in demo mode on :8000 and the frontend on :3000. Ctrl-C stops both.
# Demo mode is forced: the live client is never started by a make target.
dev:
	@exec ./scripts/dev.sh

check: check-backend check-frontend

check-backend:
	cd backend && uv run --locked ruff format --check .
	cd backend && uv run --locked ruff check .
	cd backend && uv run --locked mypy
	cd backend && uv run --locked pytest -q
	@# The eval set, replayed from recordings: free, no key. Fails on any missed threshold.
	cd backend && uv run --locked python -m tools.run_evals

check-frontend:
	cd frontend && $(NODE) npm run lint
	@# The API types are generated from backend/openapi.json. Fails if the committed file is stale.
	cd frontend && $(NODE) npm run types:check
	cd frontend && $(NODE) npm run typecheck
	cd frontend && $(NODE) npm run test
	cd frontend && $(NODE) npm run build

# Writes backend/openapi.json from the code. No server and no key. A test fails if it is stale.
openapi:
	cd backend && uv run --locked python -m tools.write_openapi

# Formats one file. Called by the edit hook. Python only: the frontend has no
# formatter, so other files are left as written and eslint covers them in `check`.
format:
	@test -n "$(FILE)" || { echo "usage: make format FILE=<path>" >&2; exit 2; }
	@case "$(abspath $(FILE))" in \
	  $(ROOT)backend/*.py) cd backend && uv run --locked ruff format -q "$(abspath $(FILE))" ;; \
	  *) : ;; \
	esac
