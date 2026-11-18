"""Step 6: the LLM writes about the summary; it never sees raw SMS and never does arithmetic."""
import json
import re

from . import llm


def _numbers(obj):
    if isinstance(obj, dict):
        obj = list(obj.values())
    if isinstance(obj, list):
        return [n for item in obj for n in _numbers(item)]
    return [float(obj)] if isinstance(obj, (int, float)) and not isinstance(obj, bool) else []


def ungrounded(text: str, summary: dict) -> list[str]:
    """₹ figures in the text that are not in the summary (rounding to the rupee is allowed)."""
    allowed = _numbers(summary)
    cited = re.findall(r"₹\s?(\d(?:[\d,]*\d)?(?:\.\d+)?)", text)
    return [c for c in cited if not any(abs(float(c.replace(",", "")) - a) < 1 for a in allowed)]


def generate(summary: dict) -> tuple[str, list[str]]:
    """Returns (insights text, ₹ figures that still aren't in the summary after one retry)."""
    prompt = llm.load_prompt("insights.txt", summary_json=json.dumps(summary, indent=1, ensure_ascii=False))
    text = llm.call(None, prompt)
    bad = ungrounded(text, summary)
    if bad:
        text = llm.call(None, prompt + "\n\nYour previous draft used figures that are not in the summary: "
                        + ", ".join("₹" + b for b in bad) + ". Rewrite it using only numbers from the summary.")
        bad = ungrounded(text, summary)
    return text, bad
