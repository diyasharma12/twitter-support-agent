.PHONY: setup index profile threads sample eval test clean

PY ?= python3

setup:
	$(PY) -m venv .venv
	./.venv/bin/pip install --upgrade pip
	./.venv/bin/pip install -r requirements.txt
	@echo "Now: cp .env.example .env and add your GEMINI_API_KEY"

index:            ## one-time: 3M-row CSV -> sqlite index (~2-3 min)
	$(PY) scripts/build_index.py

profile:          ## per-brand tweet/thread counts, to choose a brand
	$(PY) scripts/profile_brands.py

threads:          ## reconstruct customer<->brand threads for the chosen brand
	$(PY) scripts/build_threads.py

sample:           ## deterministic subsample that gets committed
	$(PY) scripts/make_sample.py

eval:             ## headline numbers — must finish in <15 min
	$(PY) scripts/run_eval.py

test:
	$(PY) -m pytest -q

clean:
	rm -rf data/interim/* reports/*
