# Hiver SDE Intern assignment — AI customer-support agent

> Status: scaffolding. Headline numbers land here once `make eval` runs.

## What this is
An AI support agent for **one brand** from the Kaggle *Customer Support on Twitter*
dataset. It classifies an incoming customer message into a data-derived intent set,
drafts a reply grounded in how this brand historically resolved similar issues, and
decides whether to auto-handle or escalate, with a stated reason.

The evaluation matters more than the agent, so most of this README is about how the
numbers were produced and where they mislead.

## Reproduce the headline results in under 15 minutes
```bash
make setup                 # venv + deps
cp .env.example .env       # add your GEMINI_API_KEY
make eval                  # runs on the committed subsample
```
The full 3M-row dataset is **not** required: `data/sample/` holds the committed
subsample and `data/golden/` the hand-labelled evaluation set. To rebuild from raw:
```bash
# put twcs.csv in data/raw/ first
make index && make profile   # choose a brand, set it in config.yaml
make threads && make sample
```

## Sections still to write
- [ ] Problem framing: what "good" means for this brand, and what I chose not to build
- [ ] Golden set: how I sampled and labelled 150–250 examples
- [ ] Results vs. a trivial and a simple baseline
- [ ] LLM-as-judge rubric and its agreement with my own labels
- [ ] Top 5 failure modes with real examples and hypotheses
- [ ] **What is misleading about my headline number**
- [ ] What I'd do next with one more week

See also [`DECISIONS.md`](DECISIONS.md) and [`CREDITS.md`](CREDITS.md).
