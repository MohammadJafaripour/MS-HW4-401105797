PYTHON ?= python
VENV := .venv

ifeq ($(OS),Windows_NT)
VENV_PYTHON := $(VENV)/Scripts/python.exe
else
VENV_PYTHON := $(VENV)/bin/python
endif

.DEFAULT_GOAL := help

.PHONY: help venv install install-dev run test test-api test-swagger validate-swagger schema clean clean-all

help:
	@echo "Mini Task Manager commands:"
	@echo "  make install           Create the virtual environment and install runtime dependencies"
	@echo "  make install-dev       Install runtime and test dependencies"
	@echo "  make run               Start the API on http://127.0.0.1:8000"
	@echo "  make test              Run all tests"
	@echo "  make test-api          Run GraphQL API tests"
	@echo "  make test-swagger      Run Swagger/OpenAPI tests"
	@echo "  make validate-swagger  Validate swagger.yaml against OpenAPI 3.1"
	@echo "  make schema            Print the generated GraphQL schema"
	@echo "  make clean             Remove caches and the local SQLite database"
	@echo "  make clean-all         Also remove the virtual environment"

$(VENV_PYTHON):
	$(PYTHON) -m venv $(VENV)

venv: $(VENV_PYTHON)

install: venv
	$(VENV_PYTHON) -m pip install -r requirements.txt

install-dev: venv
	$(VENV_PYTHON) -m pip install -r requirements-dev.txt

run: install
	$(VENV_PYTHON) -m app

test: install-dev
	$(VENV_PYTHON) -m pytest -q

test-api: install-dev
	$(VENV_PYTHON) -m pytest -q tests/test_api.py

test-swagger: install-dev
	$(VENV_PYTHON) -m pytest -q tests/test_swagger.py

validate-swagger: install-dev
	$(VENV_PYTHON) -c "from pathlib import Path; import yaml; from openapi_spec_validator import validate; validate(yaml.safe_load(Path('swagger.yaml').read_text(encoding='utf-8'))); print('swagger.yaml is valid OpenAPI 3.1')"

schema: install
	$(VENV_PYTHON) -c "from app.presentation.graphql.schema import schema; print(schema.as_str())"

clean:
	$(PYTHON) -c "from pathlib import Path; import shutil; root=Path('.'); paths=[root/'.pytest_cache', *[p for p in root.rglob('__pycache__') if '.venv' not in p.parts]]; [shutil.rmtree(p, ignore_errors=True) for p in paths]; (root/'task_manager.db').unlink(missing_ok=True)"

clean-all: clean
	$(PYTHON) -c "import shutil; shutil.rmtree('.venv', ignore_errors=True)"

