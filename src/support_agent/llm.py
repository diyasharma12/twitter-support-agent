"""The single door to the LLM, with a swappable provider.

Why a wrapper instead of calling an SDK directly:
  * Free-tier quota is the binding constraint on this project. Every prompt/response pair
    is cached on disk by hash, so re-running the eval costs zero API calls and published
    results are reproducible without a key (given the cache).
  * Two rate limiters, not one. A `RateLimiter` floors the gap between request starts, and
    a `TokenBudget` separately paces against a tokens-per-minute ceiling. This wrapper
    used to throttle by request count alone, on the assumption that Groq's free tier was
    ~25-30 requests/minute. A live probe of the API's own rate-limit headers showed the
    real, tighter constraint: 8,000 tokens/minute per model. A classify+draft pair for one
    message can cost 1,000+ tokens, so the old limiter would let a cold run (no cache)
    sail past that ceiling, get 429'd repeatedly, and blow the grader's 15-minute budget
    well past 15 minutes rather than by a little. See DECISIONS.md #17.
  * One place for retries, so a transient 429/503 does not kill a 200-example run.
  * One place to swap providers. This earned itself within an hour: Gemini retired the
    configured model mid-project and its replacement turned out to allow 20 requests per
    DAY on the free tier, against the ~570 this evaluation needs. Switching to Groq is
    now a one-line config change, not a rewrite. See DECISIONS.md #12.

Groq is reached over its OpenAI-compatible HTTP endpoint using the standard library, so
no extra dependency and no extra install time in the grader's 15-minute budget.
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

from .config import REPO_ROOT, load_config

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


class RateLimiter:
    """Crude but sufficient: never start more than N requests per rolling minute.

    A floor, not the binding constraint — see `TokenBudget` below for the one that
    actually matters on Groq's free tier.
    """

    def __init__(self, per_minute: int):
        self.min_interval = 60.0 / max(per_minute, 1)
        self._lock = threading.Lock()
        self._last = 0.0

    def wait(self) -> None:
        with self._lock:
            gap = time.monotonic() - self._last
            if gap < self.min_interval:
                time.sleep(self.min_interval - gap)
            self._last = time.monotonic()


class TokenBudget:
    """Paces calls to stay under a tokens-per-minute ceiling.

    A request-count limiter can't see this: a live probe of Groq's own rate-limit
    headers (`x-ratelimit-limit-tokens`, `x-ratelimit-reset-tokens`) showed the free tier
    caps each model at 8,000 tokens/minute, refilling continuously. Real usage is only
    known after a call returns, so this keeps a rolling window of ACTUAL reported usage
    and, before each new call, waits if the recent average call would push that window
    over budget. The average self-calibrates from real responses instead of guessing a
    token count from prompt length.

    `window_seconds` defaults to 60 (Groq's real window) and is only ever overridden in
    tests, so the pacing logic can be exercised without a real 60-second wait.
    """

    def __init__(self, tokens_per_minute: int, window_seconds: float = 60.0):
        self.budget = tokens_per_minute
        self.window_seconds = window_seconds
        self._lock = threading.Lock()
        self._window: list[tuple[float, int]] = []
        self._avg = tokens_per_minute / 10  # seed guess before any real call has happened

    def _trim(self, now: float) -> None:
        self._window = [(t, n) for t, n in self._window if now - t < self.window_seconds]

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            self._trim(now)
            used = sum(n for _, n in self._window)
            if self._window and used + self._avg > self.budget:
                sleep_for = self.window_seconds - (now - self._window[0][0])
                if sleep_for > 0:
                    time.sleep(sleep_for)

    def record(self, tokens: int) -> None:
        with self._lock:
            now = time.monotonic()
            self._window.append((now, tokens))
            self._trim(now)
            self._avg = 0.7 * self._avg + 0.3 * tokens


def _require_key(provider: str) -> str:
    var = {"gemini": "GEMINI_API_KEY", "groq": "GROQ_API_KEY"}[provider]
    key = os.environ.get(var)
    if not key:
        raise RuntimeError(
            f"{var} is not set. Add it to .env. "
            + ("Get one free at https://console.groq.com/keys"
               if provider == "groq" else
               "Get one free at https://aistudio.google.com/apikey")
        )
    return key


class LLM:
    def __init__(self, cfg: dict | None = None, model: str | None = None):
        cfg = cfg or load_config()
        self.cfg = cfg["llm"]
        self.provider = self.cfg.get("provider", "gemini")
        # `model` lets one process run two different models (the drafter and the judge)
        # through the same cache and rate limiter.
        self.model = model or self.cfg["model"]
        self.cache_dir = REPO_ROOT / self.cfg["cache_dir"]
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.limiter = RateLimiter(self.cfg["requests_per_minute"])
        self.tokens = TokenBudget(self.cfg["tokens_per_minute"])
        self._gemini = None
        self._groq_sdk = None  # None = untried, False = unavailable, else a client

    # --- providers ------------------------------------------------------------
    # Each returns (text, total_tokens_used) so the caller can feed TokenBudget real
    # numbers instead of a guess.

    def _call_gemini(self, prompt: str, temperature: float, max_tokens: int) -> tuple[str, int]:
        import google.generativeai as genai

        if self._gemini is None:
            genai.configure(api_key=_require_key("gemini"))
            self._gemini = genai
        model = self._gemini.GenerativeModel(
            self.model,
            generation_config={"temperature": temperature, "max_output_tokens": max_tokens},
        )
        resp = model.generate_content(prompt)
        usage = getattr(resp, "usage_metadata", None)
        used = getattr(usage, "total_token_count", 0) or 0
        return (resp.text or "").strip(), used

    def _call_groq(self, prompt: str, temperature: float, max_tokens: int) -> tuple[str, int]:
        """Prefer the official client; fall back to raw HTTP.

        Groq sits behind Cloudflare, which rejects urllib's default user-agent with a
        403/1010 before the request ever reaches the API — an error that looks exactly
        like a bad key but is not one. The SDK sends a normal user-agent, so it is tried
        first; the HTTP path keeps a hand-set user-agent for environments where the SDK
        is not installed. See DECISIONS.md #12.
        """
        if self._groq_sdk is not False:
            try:
                if self._groq_sdk is None:
                    from groq import Groq

                    self._groq_sdk = Groq(api_key=_require_key("groq"))
                extra = {}
                if "gpt-oss" in self.model:
                    # These models reason before answering and bill those tokens against
                    # max_tokens. Low effort keeps replies inside the budget and keeps
                    # reasoning text out of the JSON we have to parse.
                    extra["reasoning_effort"] = "low"
                resp = self._groq_sdk.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **extra,
                )
                text = (resp.choices[0].message.content or "").strip()
                used = getattr(getattr(resp, "usage", None), "total_tokens", 0) or 0
                return text, used
            except ImportError:
                self._groq_sdk = False  # not installed; use the HTTP path below

        body = json.dumps({
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }).encode()
        req = urllib.request.Request(
            GROQ_URL,
            data=body,
            headers={
                "Authorization": f"Bearer {_require_key('groq')}",
                "Content-Type": "application/json",
                "User-Agent": "hiver-support-agent/1.0 (python-urllib)",
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                payload = json.loads(resp.read())
        except urllib.error.HTTPError as err:
            detail = err.read().decode()[:300]
            hint = ""
            if err.code == 403 and "1010" in detail:
                hint = ("\n  This is Cloudflare rejecting the user-agent, not a bad key. "
                        "Install the official client: .venv/bin/pip install groq")
            raise RuntimeError(f"Groq HTTP {err.code}: {detail}{hint}") from err
        text = payload["choices"][0]["message"]["content"].strip()
        used = payload.get("usage", {}).get("total_tokens", 0) or 0
        return text, used

    def _call(self, prompt: str, temperature: float, max_tokens: int) -> tuple[str, int]:
        if self.provider == "groq":
            return self._call_groq(prompt, temperature, max_tokens)
        return self._call_gemini(prompt, temperature, max_tokens)

    # --- public -----------------------------------------------------------------

    def _cache_path(self, prompt: str, temperature: float, max_tokens: int) -> Path:
        key = hashlib.sha256(
            json.dumps(
                {"p": self.provider, "m": self.model, "t": temperature,
                 "mt": max_tokens, "q": prompt},
                sort_keys=True,
            ).encode()
        ).hexdigest()
        return self.cache_dir / f"{key}.json"

    def complete(
        self,
        prompt: str,
        temperature: float = 0.0,
        use_cache: bool = True,
        max_tokens: int | None = None,
    ) -> str:
        max_tokens = max_tokens or self.cfg.get("max_tokens_default", 256)
        path = self._cache_path(prompt, temperature, max_tokens)
        if use_cache and path.exists():
            return json.loads(path.read_text())["response"]

        last_err: Exception | None = None
        for attempt in range(5):
            try:
                self.limiter.wait()
                self.tokens.wait()
                text, used = self._call(prompt, temperature, max_tokens)
                # Fall back to a rough estimate if a provider ever omits usage, so the
                # budget still has something to learn from rather than assuming zero cost.
                self.tokens.record(used or (len(prompt) // 4 + max_tokens))
                path.write_text(json.dumps({"prompt": prompt, "response": text}))
                return text
            except Exception as err:  # noqa: BLE001 - providers throw several shapes
                last_err = err
                time.sleep(min(2**attempt, 30))
        raise RuntimeError(f"LLM call failed after retries: {last_err}")

    def complete_json(
        self, prompt: str, temperature: float = 0.0, max_tokens: int | None = None
    ) -> dict:
        """Same, but strips markdown fences and parses JSON.

        Unparseable output is itself a finding, so it is not silently repaired here —
        the caller decides whether to count it as a model failure.
        """
        raw = self.complete(prompt, temperature=temperature, max_tokens=max_tokens)
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```")[1]
            cleaned = cleaned[4:] if cleaned.startswith("json") else cleaned
        return json.loads(cleaned.strip())
