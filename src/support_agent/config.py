"""Loads config.yaml and .env once, so no other module hardcodes a path or a key.

Kept deliberately tiny: a dict-like object plus a repo-root helper. If you ever need a
setting in two places, it belongs in config.yaml, not in a constant.
"""
from __future__ import annotations

import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]


def load_config(path: str | Path | None = None) -> dict:
    """Read config.yaml and .env. Returns the raw config dict."""
    load_dotenv(REPO_ROOT / ".env")
    cfg_path = Path(path) if path else REPO_ROOT / "config.yaml"
    with open(cfg_path) as fh:
        cfg = yaml.safe_load(fh)
    return cfg


def resolve(path_template: str, **kwargs) -> Path:
    """Turn a config path template like 'data/x_{brand}.jsonl' into an absolute Path."""
    return REPO_ROOT / path_template.format(**kwargs)


def require_api_key() -> str:
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Copy .env.example to .env and add your key "
            "from https://aistudio.google.com/apikey"
        )
    return key
