"""List the models this API key can actually use, and probe their free-tier quota.

Written after a run died on `gemini-2.0-flash` (retired) and then on `gemini-3.6-flash`
(20 requests per DAY on the free tier). Published rate-limit tables were out of date for
both, so this asks the provider directly instead of trusting a blog post.
"""
import os
import sys

import _bootstrap  # noqa: F401
from support_agent.config import REPO_ROOT

from dotenv import load_dotenv

load_dotenv(REPO_ROOT / ".env")

import google.generativeai as genai  # noqa: E402

genai.configure(api_key=os.environ["GEMINI_API_KEY"])

print("Models supporting generateContent:\n")
names = []
for m in genai.list_models():
    if "generateContent" in getattr(m, "supported_generation_methods", []):
        names.append(m.name.replace("models/", ""))
        print(f"  {m.name.replace('models/', '')}")

if "--probe" in sys.argv:
    print("\nProbing each with one tiny call (this uses quota):\n")
    for n in names:
        if "pro" in n or "image" in n or "tts" in n or "embed" in n:
            continue
        try:
            genai.GenerativeModel(n).generate_content("say ok")
            print(f"  {n:<34} OK")
        except Exception as e:
            msg = str(e).split("\n")[0][:80]
            print(f"  {n:<34} {msg}")
