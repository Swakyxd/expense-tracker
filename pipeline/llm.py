"""The only place that talks to an LLM. To swap providers, rewrite call()."""
import hashlib
import json
import os
import re
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

ROOT = Path(__file__).parent.parent
load_dotenv(ROOT / ".env")
MODEL = os.getenv("MODEL_NAME") or "gemini-3.5-flash"

CACHE_DIR: Path | None = None  # eval sets this so re-runs are free; the app never writes SMS to disk
SALT = ""                      # eval sets "run1", "run2"... so repeated runs are separate API calls
STATS: list[dict] = []         # one {prompt_tokens, output_tokens, latency} per call

_client = None


def load_prompt(name: str, **values) -> str:
    text = (ROOT / "prompts" / name).read_text(encoding="utf-8")
    for key, value in values.items():  # not str.format: the prompts contain literal JSON braces
        text = text.replace("{" + key + "}", str(value))
    return text


def call(system: str | None, user: str, json_schema=None, json_mode: bool = False) -> str:
    """One LLM call at temperature 0. Returns the response text ("" if the model returned nothing)."""
    key = hashlib.sha256(json.dumps([MODEL, system, user, str(json_schema), json_mode, SALT]).encode()).hexdigest()
    cached = CACHE_DIR / f"{key}.json" if CACHE_DIR else None
    if cached and cached.exists():
        entry = json.loads(cached.read_text(encoding="utf-8"))
        STATS.append(entry["stats"])
        return entry["text"]

    global _client
    if _client is None:
        if not os.getenv("GEMINI_API_KEY"):
            raise RuntimeError("GEMINI_API_KEY is not set. Copy .env.example to .env and add your key.")
        # timeout is in ms; without one a stalled connection hangs the app forever
        _client = genai.Client(api_key=os.environ["GEMINI_API_KEY"], http_options=types.HttpOptions(timeout=180_000))

    config = types.GenerateContentConfig(
        system_instruction=system,
        temperature=0,
        response_mime_type="application/json" if (json_schema or json_mode) else None,
        response_schema=json_schema,
    )
    for attempt in range(6):
        start = time.time()
        try:
            response = _client.models.generate_content(model=MODEL, contents=user, config=config)
            break
        except Exception as e:
            # retry rate limits (429), 5xx and dropped/timed-out connections: back off 5s, 10s, ... 80s, then give up
            code = e.code if isinstance(e, errors.APIError) else None
            network = type(e).__module__.startswith(("httpx", "httpcore"))
            wait = 5 * 2**attempt
            if code == 429:
                asked = re.search(r"'retryDelay': '(\d+)", str(e))  # the API says how long to wait
                wait = int(asked.group(1)) + 1 if asked else wait
                if wait > 120:  # a per-day quota, not a per-minute one: retrying is pointless
                    raise RuntimeError(
                        f"Daily free-tier quota for {MODEL} is used up (resets in about {wait // 3600}h {wait % 3600 // 60}m). "
                        "Set MODEL_NAME in .env to another model, or enable billing on the key.") from None
            if attempt == 5 or not (network or code == 429 or (code or 0) >= 500):
                raise
            time.sleep(wait)

    usage = response.usage_metadata
    stats = {
        "prompt_tokens": (usage.prompt_token_count or 0) if usage else 0,
        "output_tokens": ((usage.candidates_token_count or 0) + (usage.thoughts_token_count or 0)) if usage else 0,
        "latency": round(time.time() - start, 3),
    }
    STATS.append(stats)
    text = response.text or ""
    if cached:
        cached.parent.mkdir(parents=True, exist_ok=True)
        cached.write_text(json.dumps({"text": text, "stats": stats}), encoding="utf-8")
    return text
