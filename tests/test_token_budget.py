"""The tokens-per-minute limiter is what keeps a cold `make eval` under 15 minutes on
Groq's free tier (see the rate-limiting decision) — a silently-wrong pacer would only
show up as a real 429 storm during a live run, so the pacing logic gets a fast fixture
here instead, using a short window so the test doesn't actually wait a minute.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from support_agent.llm import TokenBudget


def test_waits_when_recent_usage_would_exceed_budget():
    tb = TokenBudget(tokens_per_minute=100, window_seconds=0.3)
    tb.record(90)  # most of the budget already spent in this window
    start = time.monotonic()
    tb.wait()
    assert time.monotonic() - start > 0.1


def test_does_not_wait_when_well_under_budget():
    tb = TokenBudget(tokens_per_minute=100_000, window_seconds=0.3)
    tb.record(50)
    start = time.monotonic()
    tb.wait()
    assert time.monotonic() - start < 0.05


def test_old_usage_falls_out_of_the_window():
    tb = TokenBudget(tokens_per_minute=100, window_seconds=0.2)
    tb.record(90)
    time.sleep(0.25)  # let the window expire
    start = time.monotonic()
    tb.wait()
    assert time.monotonic() - start < 0.05


def test_average_learns_from_real_usage():
    tb = TokenBudget(tokens_per_minute=1000)
    before = tb._avg
    tb.record(2000)
    assert tb._avg > before
