PYTHON ?= python
COSMOS = mcr.microsoft.com/cosmosdb/linux/azure-cosmos-emulator:vnext-EN20261019@sha256:db53613dae19d0a3d5ad50688d14aa6e957af082dafea56b52e1bd3a6b3f1406

.PHONY: install lint type test budget check emulator index

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

emulator:
	docker run -d --rm --name juriscope-cosmos -p 8091:8081 -p 8090:8080 $(COSMOS) --enable-explorer false

index:
	$(PYTHON) -m ops.index --target local
