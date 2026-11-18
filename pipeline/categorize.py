"""Step 4: rules first, cached LLM fallback for merchants the rules don't know."""
import json
import re
from pathlib import Path

from rapidfuzz import fuzz

from . import llm
from .schema import CATEGORIES

DATA = Path(__file__).parent.parent / "data"
RULES = json.loads((DATA / "merchant_rules.json").read_text(encoding="utf-8"))
CACHE_FILE: Path | None = DATA / "cache.json"  # eval sets None to keep runs independent
_cache: dict[str, str] = json.loads(CACHE_FILE.read_text(encoding="utf-8")) if CACHE_FILE.exists() else {}

# ponytail: keyword heuristic for own-account moves and card bill payments; needs the user's account list to be exact
SELF_TRANSFER = re.compile(r"\bown a/?c\b|\bself\b|received (on|towards|for) .{0,40}credit card", re.I)


def _rule(row: dict) -> str | None:
    text = row["raw_sms"].lower()
    if row["mode"] == "ATM":
        return "Cash Withdrawal"
    if SELF_TRANSFER.search(text):
        return "Transfers to People"
    if row["type"] == "credit":
        if row.get("status") == "reversed" or re.search(r"refund|revers|cashback", text):
            return "Refund"
        if re.search(r"salary|stipend|interest", text):
            return "Income"
    merchant = (row["merchant"] or "").lower()
    best = (0, 0, None)  # (score, keyword length, category): longest keyword wins ties
    for category, keywords in RULES.items():
        for kw in keywords:
            if len(kw) <= 4:  # short keywords fuzzy-match everything ("ola" in "cola"): whole word only
                score = 100 if re.search(rf"\b{re.escape(kw)}\b", merchant) else 0
            else:
                score = fuzz.partial_ratio(kw, merchant) if len(merchant) >= len(kw) else fuzz.ratio(kw, merchant)
            if score >= 85:
                best = max(best, (score, len(kw), category))
    return best[2]


def _ask_llm(merchants: list[str]) -> dict[str, str]:
    raw = llm.call(llm.load_prompt("categorize.txt"), "\n".join(merchants), json_mode=True)
    try:
        answer = json.loads(raw)
    except ValueError:
        return {}
    return {m: c for m, c in answer.items() if c in CATEGORIES} if isinstance(answer, dict) else {}


def categorize(rows: list[dict], use_rules: bool = True, use_llm: bool = True) -> list[dict]:
    """Adds category, category_source and self_transfer to every row (in place)."""
    todo = []
    for row in rows:
        row["self_transfer"] = bool(row["is_transaction"] and SELF_TRANSFER.search(row["raw_sms"]))
        row["category"] = row["category_source"] = None
        if not row["is_transaction"]:
            continue
        category = _rule(row) if use_rules else None
        if category:
            row["category"], row["category_source"] = category, "rule"
        elif row["merchant"] and use_llm:
            todo.append(row)
        else:
            row["category"], row["category_source"] = "Other", "rule"

    unknown = sorted({r["merchant"] for r in todo} - _cache.keys())
    if unknown:
        answer = _ask_llm(unknown)
        _cache.update(answer)
        if CACHE_FILE:  # people's names stay out of the on-disk cache
            keep = {m: c for m, c in _cache.items() if c != "Transfers to People"}
            CACHE_FILE.write_text(json.dumps(keep, indent=1, ensure_ascii=False), encoding="utf-8")
    for row in todo:
        row["category"], row["category_source"] = _cache.get(row["merchant"], "Other"), "llm"
    return rows
