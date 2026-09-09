# Every target runs inside .venv once `make setup` has been run, so you never have to
# remember to activate it. Override with `make PY=python3.12 setup` if needed.
.PHONY: setup index profile threads sample eval test clean

BOOTSTRAP_PY ?= python3
VENV := .venv
PY := $(VENV)/bin/python

setup:                ## create .venv and install dependencies
	$(BOOTSTRAP_PY) -m venv $(VENV)
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install -r requirements.txt
	@echo ""
	@echo "Done. Next: cp .env.example .env  and paste your GEMINI_API_KEY into it."

index:                ## one-time: 3M-row CSV -> sqlite index (~2-3 min)
	$(PY) scripts/build_index.py

profile:              ## per-brand stats, to choose a brand on evidence
	$(PY) scripts/profile_brands.py

threads:              ## reconstruct customer<->brand threads for the chosen brand
	$(PY) scripts/build_threads.py

sample:               ## deterministic subsample that gets committed
	$(PY) scripts/make_sample.py

eval:                 ## headline numbers - must finish in <15 min
	$(PY) scripts/run_eval.py

test:
	$(PY) -m pytest -q

clean:
	rm -rf data/interim/* reports/*
