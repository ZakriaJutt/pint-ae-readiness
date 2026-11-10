# PINT AE Readiness Desk: local commands (B1). Services run directly; Docker is not used here.
PY      := backend/.venv/bin/python
PYPATH  := apps/api:apps/worker:packages/core:packages/rules:packages/rulepacks:packages/ingest
TESTDB  := postgresql+psycopg://zakria@localhost:5432/pintae_test
export PYTHONPATH := $(PYPATH)

.PHONY: venv dev dev-check migrate test test-unit test-integration lint typecheck arch parity check

venv:
	/opt/homebrew/bin/python3.12 -m venv backend/.venv
	$(PY) -m pip install -r backend/requirements.lock

dev:            ## start database checks, migrations, worker and API (port 8105); wait for /readyz
	$(PY) scripts/dev.py

dev-check:      ## OPS-04: start everything, wait for readiness, stop
	$(PY) scripts/dev.py --check

migrate:
	cd backend && ../$(PY) -m alembic -c alembic.ini upgrade head

test:           ## full suite on a freshly rebuilt pintae_test schema
	cd backend && .venv/bin/pytest

test-unit:
	cd backend && .venv/bin/pytest tests/unit

test-integration:
	cd backend && .venv/bin/pytest tests/integration

lint:
	cd backend && .venv/bin/ruff check ../apps ../packages ../scripts tests && .venv/bin/ruff format --check ../apps ../packages ../scripts tests

typecheck:
	cd backend && .venv/bin/mypy ../apps ../packages ../scripts tests

arch:           ## ARCH-01
	$(PY) scripts/check_imports.py

parity:         ## IT-11 parity and single head, against pintae_test
	$(PY) scripts/check_schema_parity.py $(TESTDB)

check: lint typecheck arch test parity
