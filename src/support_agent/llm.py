"""The single door to the LLM, with a swappable provider.

Why a wrapper instead of calling an SDK directly:
  * Free-tier quota is the binding constraint on this project. Every prompt/response pair
    is cached on disk by hash, so re-running the eval costs zero API calls and published
    results are reproducible without a key (given the cache).
  * A shared rate limiter keeps us under the free-tier requests-per-minute ceiling.
  * One place for retries, so a transient 429/503 does not kill a 200-example run.
  * One place to swap providers. This earned itself within an hour: Gemini retired the
    configured model mid-project and its replacement turned out to allow 20 requests per
    DAY on the free tier, against the ~570 this evaluation needs. Switching to Groq is
    now a one-line config change, not a rewrite. See DECISIONS.md #17.

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
    """Crude but sufficient: never start more than N requests per rolling minute."""

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
        self._gemini = None
        self._groq_sdk = None  # None = untried, False = unavailable, else a client

    # --- providers ----------------------------------------------------------

    def _call_gemini(self, prompt: str, temperature: float) -> str:
        import google.generativeai as genai

        if self._gemini is None:
            genai.configure(api_key=_require_key("gemini"))
            self._gemini = genai
        model = self._gemini.GenerativeModel(
            self.model,
            generation_config={
                "temperature": temperature,
                "max_output_tokens": self.cfg["max_output_tokens"],
            },
        )
        return (model.generate_content(prompt).text or "").strip()

    def _call_groq(self, prompt: str, temperature: float) -> str:
        """Prefer the official client; fall back to raw HTTP.

        Groq sits behind Cloudflare, which rejects urllib's default user-agent with a
        403/1010 before the request ever reaches the API — an error that looks exactly
        like a bad key but is not one. The SDK sends a normal user-agent, so it is tried
        first; the HTTP path keeps a hand-set user-agent for environments where the SDK
        is not installed. See DECISIONS.md #18.
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
                    max_tokens=self.cfg["max_output_tokens"],
                    **extra,
                )
                return (resp.choices[0].message.content or "").strip()
            except ImportError:
                self._groq_sdk = False  # not installed; use the HTTP path below

        body = json.dumps({
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": self.cfg["max_output_tokens"],
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
        return payload["choices"][0]["message"]["content"].strip()

    def _call(self, prompt: str, temperature: float) -> str:
        if self.provider == "groq":
            return self._call_groq(prompt, temperature)
        return self._call_gemini(prompt, temperature)

    # --- public -------------------------------------------------------------

    def _cache_path(self, prompt: str, temperature: float) -> Path:
        key = hashlib.sha256(
            json.dumps(
                {"p": self.provider, "m": self.model, "t": temperature, "q": prompt},
                sort_keys=True,
            ).encode()
        ).hexdigest()
        return self.cache_dir / f"{key}.json"

    def complete(self, prompt: str, temperature: float = 0.0, use_cache: bool = True) -> str:
        path = self._cache_path(prompt, temperature)
        if use_cache and path.exists():
            return json.loads(path.read_text())["response"]

        last_err: Exception | None = None
        for attempt in range(5):
            try:
                self.limiter.wait()
                text = self._call(prompt, temperature)
                path.write_text(json.dumps({"prompt": prompt, "response": text}))
                return text
            except Exception as err:  # noqa: BLE001 - providers throw several shapes
                last_err = err
                time.sleep(min(2**attempt, 30))
        raise RuntimeError(f"LLM call failed after retries: {last_err}")

    def complete_json(self, prompt: str, temperature: float = 0.0) -> dict:
        """Same, but strips markdown fences and parses JSON.

        Unparseable output is itself a finding, so it is not silently repaired here —
        the caller decides whether to count it as a model failure.
        """
        raw = self.complete(prompt, temperature=temperature)
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```")[1]
            cleaned = cleaned[4:] if cleaned.startswith("json") else cleaned
        return json.loads(cleaned.strip())
