PYTHON ?= python

.PHONY: install lint type test budget check

install:
	$(PYTHON) -m pip install -r requirements-dev.txt

lint:
	ruff check .
	ruff format --check .

type:
	mypy

test:
	pytest -q

budget:
	$(PYTHON) -c "from tests.test_budget import budget_counts; print(budget_counts())"

check: lint type test
