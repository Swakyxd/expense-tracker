"""Steps 2-3: batched LLM extraction, validation, and (v4 only) the repair loop."""
import json
import re
from datetime import date

from pydantic import ValidationError

from . import llm
from .schema import Sms, Transaction

BATCH_SIZE = 30  # eval E3: same accuracy as 10 with fewer requests and tokens
MAX_REPAIRS = 2


def batches(items: list, size: int = BATCH_SIZE):
    for i in range(0, len(items), size):
        yield items[i:i + size]


def check(item, sms: Sms) -> tuple[Transaction, list[str]]:
    """Schema + semantic checks for one raw output item. Invalid fields are nulled and reported, never dropped."""
    if not isinstance(item, dict):
        return Transaction(id=sms.id, is_transaction=False), ["no valid JSON object returned for this message"]
    item = {**item, "id": sms.id}
    errors = []
    try:
        tx = Transaction.model_validate(item)
    except ValidationError as e:
        for err in e.errors():
            field = err["loc"][0] if err["loc"] else "output"
            errors.append(f"{field}: {err['msg']}")
            item[field] = None
        item["is_transaction"] = bool(item.get("is_transaction"))
        tx = Transaction.model_validate(item)

    if tx.is_transaction:
        errors += [f"{f}: required when is_transaction is true" for f in ("type", "amount", "status") if getattr(tx, f) is None]
        if tx.amount is not None:
            numbers = [float(n.replace(",", "")) for n in re.findall(r"\d[\d,]*(?:\.\d+)?", sms.text)]
            if not any(abs(n - tx.amount) < 0.005 for n in numbers):
                errors.append(f"amount: {tx.amount} does not appear in the SMS text")
    if tx.date is not None:
        try:
            if date.fromisoformat(tx.date) > date.today():
                errors.append(f"date: {tx.date} is in the future")
        except ValueError:
            errors.append(f"date: '{tx.date}' is not a valid YYYY-MM-DD date")
    return tx, errors


def _loads(raw: str):
    try:
        return json.loads(raw)
    except ValueError:
        return None


def extract_batch(batch: list[Sms], version: str) -> tuple[list[dict], dict]:
    """Returns (one row per SMS, {"valid_json": parsed on first try, "repairs": repair calls made})."""
    system = llm.load_prompt(f"extract_{version}.txt", current_year=date.today().year)
    raw = llm.call(system, "\n".join(f"[{s.id}] {s.text}" for s in batch), json_schema=list[Transaction])
    parsed = _loads(raw)
    valid = isinstance(parsed, list) and all(isinstance(it, dict) for it in parsed)
    items = {it.get("id"): it for it in parsed} if valid else {}

    rows, repairs = [], 0
    for s in batch:
        item = items.get(s.id)
        tx, errors = check(item, s)
        for _ in range(MAX_REPAIRS if version == "v4" else 0):
            if not errors:
                break
            repairs += 1
            prompt = llm.load_prompt(
                "repair.txt", id=s.id, sms_text=s.text,
                previous_json=json.dumps(item) if item else raw[:500] or "(nothing)",
                error_list="\n".join(f"- {e}" for e in errors))
            item = _loads(llm.call(system, prompt, json_schema=Transaction))
            tx, errors = check(item, s)
        if tx.is_transaction and tx.date is None and s.ts:  # fall back to the SMS timestamp
            tx.date = s.ts.date().isoformat()
        rows.append(tx.model_dump() | {"needs_review": bool(errors), "errors": "; ".join(errors), "raw_sms": s.text})
    return rows, {"valid_json": valid, "repairs": repairs}
