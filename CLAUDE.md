# CLAUDE.md — project context for Claude Code

## What this repo is
A take-home assignment for the Hiver SDE Intern role. It builds an AI customer-support
agent for ONE brand from the Kaggle "Customer Support on Twitter" dataset
(`thoughtvector/customer-support-on-twitter`, ~3M tweets).

The agent must:
1. Classify an incoming customer message into a small intent set defined FROM the data.
2. Draft a reply grounded in how the brand historically resolved similar issues.
3. Decide auto-handle vs escalate-to-human, with a stated reason.

**The evaluation is worth more than the agent.** The grader explicitly says "the proof is
worth more than the system". Prioritise the golden set, the eval harness, judge-vs-human
agreement, and honest failure analysis over agent cleverness.

## Hard constraints
- `make setup && make eval` must reproduce the headline numbers in **under 15 minutes** on
  the committed subsample. Graders will not run the full dataset.
- Raw Kaggle data is NEVER committed. Only `data/golden/` and small derived samples are.
- LLM is **Gemini free tier** (no billing enabled). Every LLM call goes through
  `support_agent.llm` so it is cached to `.cache/` and rate-limited. Never call the API
  directly from a script.
- Anything borrowed (code, prompt patterns, ideas) gets a line in `CREDITS.md`.
- The author must be able to explain and modify every file live in an interview. Prefer
  small, obvious, well-named functions over clever abstractions.

## Conventions
- Python 3.11+, standard library first, `pandas`/`scikit-learn` where they earn their place.
- Package lives in `src/support_agent/`. Scripts in `scripts/` are thin CLI wrappers.
- Every module has a module-level docstring saying WHY it exists, not just what it does.
- Deterministic where possible: fixed `RANDOM_SEED` in `config.yaml`, temperature 0 for
  classification and judging.
- Tests in `tests/` with pytest. Anything involving thread reconstruction or metric maths
  gets a unit test with a hand-built tiny fixture.
- Every non-obvious decision gets appended to `DECISIONS.md` as it is made — that file is a
  graded deliverable, not an afterthought.

## Layout
```
src/support_agent/
  config.py        # loads config.yaml + .env
  llm.py           # Gemini wrapper: disk cache, retries, rate limit
  data/            # index building, brand profiling, thread reconstruction
  agent/           # classifier, retriever, reply drafter, escalation policy
  eval/            # metrics, baselines, LLM judge, judge-vs-human agreement
scripts/           # CLI entry points used by the Makefile
data/golden/       # hand-labelled golden set (COMMITTED)
reports/           # generated metric tables and figures
```

## Working style with Claude Code
- One step at a time. Write the code, run it, look at real output, then move on.
- Ask before adding a dependency.
- Do not write the report's numbers by hand — they come from `reports/`.
