"""Scoring of pipeline output against data/test_sms.csv labels."""
import re

import pandas as pd
from rapidfuzz import fuzz, utils

FIELDS = ["amount", "type", "date", "merchant", "mode", "status", "category"]


def _null(v) -> bool:
    return v is None or pd.isna(v)


def match(field: str, expected, predicted) -> bool:
    if field == "mode":  # null and OTHER both mean "no specific mode stated"
        expected, predicted = ("OTHER" if _null(v) else v for v in (expected, predicted))
    if _null(expected) or _null(predicted):
        return _null(expected) and _null(predicted)
    if field == "amount":
        return abs(float(expected) - float(predicted)) <= 0.01
    if field == "merchant":
        # token_set_ratio rather than plain ratio: "Starbucks" vs "Starbucks Coffee" is the same merchant
        return fuzz.token_set_ratio(str(expected), str(predicted), processor=utils.default_process) >= 80
    return str(expected) == str(predicted)


def score(gold: pd.DataFrame, pred: pd.DataFrame) -> dict:
    """Both frames are indexed by SMS id. Ids missing from pred count as 'not a transaction'."""
    pred = pred.reindex(gold.index)
    g = gold["is_transaction"].astype(bool)
    p = pred["is_transaction"].map(lambda v: False if _null(v) else bool(v))
    tp, fp, fn = (g & p).sum(), (~g & p).sum(), (g & ~p).sum()
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    out = {
        "detection_precision": precision,
        "detection_recall": recall,
        "detection_f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
    }
    for f in FIELDS:  # field accuracy over true transactions; a missed transaction is wrong on every field
        out[f"{f}_accuracy"] = sum(p[i] and match(f, gold.at[i, f], pred.at[i, f]) for i in gold.index[g]) / g.sum()
    out["overall_field_accuracy"] = sum(out[f"{f}_accuracy"] for f in FIELDS) / len(FIELDS)
    return out


def failures(gold: pd.DataFrame, pred: pd.DataFrame) -> list[dict]:
    """Every wrong prediction: {id, field, expected, predicted, cause, sms}."""
    pred = pred.reindex(gold.index)
    out = []
    for i in gold.index:
        g = bool(gold.at[i, "is_transaction"])
        p = not _null(pred.at[i, "is_transaction"]) and bool(pred.at[i, "is_transaction"])
        wrong = [("is_transaction", g, p)] if g != p else []
        if g and p:
            wrong = [(f, gold.at[i, f], pred.at[i, f]) for f in FIELDS if not match(f, gold.at[i, f], pred.at[i, f])]
        out += [{"id": i, "field": f, "expected": "null" if _null(e) else e, "predicted": "null" if _null(q) else q,
                 "cause": likely_cause(f, e, q, gold.at[i, "sms"]),
                 "sms": gold.at[i, "sms"]} for f, e, q in wrong]
    return out


def likely_cause(field: str, expected, predicted, sms: str) -> str:
    """Auto-suggested first guess for the failure log; review by hand."""
    if field == "is_transaction":
        return "noise counted as a transaction" if predicted else "real transaction missed (filtered out or rejected)"
    if _null(predicted) and field != "mode":
        return "returned null although the value is in the SMS"
    if _null(expected):
        return "value invented or inferred; the SMS does not state it"
    if field == "amount":
        balances = re.findall(r"(?:bal|lmt|limit|due)[^\d]{0,20}(\d[\d,]*(?:\.\d+)?)", sms, re.I)
        if any(abs(float(b.replace(",", "")) - float(predicted)) < 0.01 for b in balances):
            return "balance / limit read as the amount"
        return "wrong number picked"
    return {
        "type": "debit/credit direction confused (e.g. 'credited to X' inside a debit SMS)",
        "date": "date format not normalised correctly",
        "merchant": "wrong party or name not cleaned",
        "mode": "payment mode inferred or confused (e.g. autopay vs the rail it ran on)",
        "status": "failed / reversed wording misread",
        "category": "merchant not in rules; LLM fallback chose differently (or upstream merchant error)",
    }[field]
