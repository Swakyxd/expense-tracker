"""Offline self-check: python test_pipeline.py  (the LLM is replaced by a stub that answers from the labels)."""
import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent / "eval"))
from metrics import score  # noqa: E402
from run_eval import load_gold, run_categorizer, run_pipeline  # noqa: E402

from pipeline import categorize as cat, llm  # noqa: E402
from pipeline.aggregate import summarize  # noqa: E402
from pipeline.extract import check  # noqa: E402
from pipeline.insights import generate, ungrounded  # noqa: E402
from pipeline.preprocess import mask, parse_text, preprocess  # noqa: E402
from pipeline.schema import Sms, Transaction  # noqa: E402

GOLD = load_gold()
cat.CACHE_FILE = None
WRONG_FIRST = set()  # ids the stub gets wrong on its first answer (balance instead of amount)


def stub_llm(system, user, json_schema=None, json_mode=False):
    llm.STATS.append({"prompt_tokens": 1, "output_tokens": 1, "latency": 0.0})

    def answer(i, corrupt):
        g = GOLD.loc[i]
        if not g["is_transaction"]:
            return {"id": i, "is_transaction": False}
        fields = {k: (None if pd.isna(g[k]) else g[k]) for k in ("type", "amount", "merchant", "date", "mode", "status")}
        return {"id": i, "is_transaction": True, **fields} | ({"amount": 99999.0} if corrupt else {})

    ids = [int(i) for i in re.findall(r"^\[(\d+)\]", user, re.M)]
    if json_schema is Transaction:  # repair call
        return json.dumps(answer(int(re.search(r"\[(\d+)\]", user).group(1)), False))
    if json_schema:  # extraction batch
        return json.dumps([answer(i, i in WRONG_FIRST) for i in ids])
    if json_mode:  # categorize
        return json.dumps({m: "Transfers to People" for m in user.splitlines()})
    return "- You spent ₹1,000 in total.\n- A made-up figure: ₹123,456."


llm.call = stub_llm


def test_preprocess():
    msgs = [Sms(i, s) for i, s in GOLD["sms"].items()]
    kept, noise, dups = preprocess(msgs)
    assert not GOLD.loc[[m.id for m in noise], "is_transaction"].any(), "filter dropped a real transaction"
    assert (len(kept), len(noise), dups) == (44, 16, 0)

    m = mask("A/c XXXXXXXX3390 Ref 431622819023 call 9876543210 or 18002586161, mail a.b@x.co.in, to rapido@ybl, acct 123456789012345")
    assert m == "A/c XX3390 Ref [REF] call [PHONE] or 18002586161, mail [EMAIL], to rapido@ybl, acct XX2345", m

    t = datetime(2026, 11, 1, 10, 0)
    a = "Sent Rs.289.00 to SWIGGY Ref 428812340002"
    b = "Paid Rs.289.00 to SWIGGY via UPI. Ref 428812340002"
    assert len(preprocess([Sms(1, a, t), Sms(2, b, t + timedelta(minutes=2))])[0]) == 1    # duplicate
    assert len(preprocess([Sms(1, a, t), Sms(2, b, t + timedelta(hours=2))])[0]) == 2      # same ref, too far apart
    assert len(parse_text("one\ntwo\nthree")) == 3 and len(parse_text("one\nstill one\n\ntwo")) == 2


def test_check():
    sms = Sms(1, "Rs.1,850.00 spent on Card XX7788 at AMAZON on 10-11-26. Avl Lmt: Rs.48,150.00")
    ok = {"is_transaction": True, "type": "debit", "amount": 1850, "status": "success", "date": "2026-11-10"}
    assert check(ok, sms)[1] == []
    assert "does not appear" in check(ok | {"amount": 1580}, sms)[1][0]
    assert "future" in check(ok | {"date": "2999-01-01"}, sms)[1][0]
    assert "not a valid" in check(ok | {"date": "10-11-26"}, sms)[1][0]
    assert len(check({"is_transaction": True}, sms)[1]) == 3            # type, amount, status required
    tx, errors = check(ok | {"mode": "NETBANKING"}, sms)                 # bad enum is nulled, row survives
    assert tx.mode is None and tx.amount == 1850 and errors
    assert check(None, sms)[1] and check({"is_transaction": False}, sms)[1] == []


def test_pipeline_and_repair():
    WRONG_FIRST.clear()
    _, m = run_pipeline(GOLD, "v3")
    assert m["detection_f1"] == 1 and m["amount_accuracy"] == 1 and m["api_calls"] == 7, m  # 6 batches + 1 categorize

    WRONG_FIRST.update({2, 15})
    pred, m = run_pipeline(GOLD, "v3")                      # no repair loop: flagged, not dropped
    assert pred.loc[[2, 15], "needs_review"].all() and m["amount_accuracy"] == 38 / 40
    pred, m = run_pipeline(GOLD, "v4")                      # repair loop fixes both
    assert not pred["needs_review"].any() and m["amount_accuracy"] == 1 and m["repairs_per_batch"] == 2 / 6
    _, m = run_pipeline(GOLD, "v4", use_filter=True)
    assert m["sms_sent_to_llm"] == 44 and m["transactions_wrongly_dropped"] == 0 and m["detection_f1"] == 1
    WRONG_FIRST.clear()

    empty = pd.DataFrame({"is_transaction": []}).reindex(columns=["is_transaction", "amount", "type", "date", "merchant", "mode", "status", "category"])
    assert score(GOLD, empty)["detection_recall"] == 0


def test_categorize_rules():
    _, m = run_categorizer(GOLD, use_rules=True, use_llm=False)
    print(f"  rules-only category accuracy on gold merchants: {m['category_accuracy']:.0%}")
    assert m["category_accuracy"] >= 0.7 and m["api_calls"] == 0
    rows = [{"is_transaction": True, "raw_sms": s, "merchant": mer, "mode": mode, "type": typ} for s, mer, mode, typ in [
        ("paid", "PYU*ZOMATOONLINE", "CARD", "debit"), ("paid", "Coca Cola", "UPI", "debit"),
        ("withdrawn", None, "ATM", "debit"), ("Refund of Rs.5 from SWIGGY credited", "Swiggy", "UPI", "credit"),
        ("paid", "Amazon Prime Video", "CARD", "debit"), ("Rs.500 transferred to own a/c XX12", None, "NEFT_IMPS", "debit")]]
    cat.categorize(rows, use_llm=False)
    assert [r["category"] for r in rows] == ["Food & Dining", "Other", "Cash Withdrawal", "Refund",
                                             "Entertainment & Subscriptions", "Transfers to People"]
    assert [r["self_transfer"] for r in rows] == [False] * 5 + [True]

    from metrics import match
    assert match("mode", None, "OTHER") and match("mode", "OTHER", None) and not match("mode", "UPI", None)
    hard = load_gold("test_sms_hard.csv")   # the stub answers from the labels, so only the rules can lose points
    assert len(hard) == 24 and hard["is_transaction"].sum() == 16


def test_aggregate_and_insights():
    df = pd.DataFrame([
        {"is_transaction": True, "status": "success", "type": "debit", "amount": 800.0, "merchant": "Swiggy", "date": "2026-11-02", "category": "Food & Dining", "self_transfer": False},
        {"is_transaction": True, "status": "success", "type": "debit", "amount": 150.0, "merchant": "Uber", "date": "2026-11-11", "category": "Travel & Transport", "self_transfer": False},
        {"is_transaction": True, "status": "success", "type": "debit", "amount": 50.0, "merchant": "Swiggy", "date": None, "category": "Food & Dining", "self_transfer": True},
        {"is_transaction": True, "status": "failed", "type": "debit", "amount": 5000.0, "merchant": "Ola", "date": "2026-11-03", "category": "Travel & Transport", "self_transfer": False},
        {"is_transaction": True, "status": "success", "type": "credit", "amount": 3000.0, "merchant": "ACME", "date": "2026-11-01", "category": "Income", "self_transfer": False},
        {"is_transaction": False, "status": None, "type": None, "amount": None, "merchant": None, "date": None, "category": None, "self_transfer": False},
    ])
    s = summarize(df)
    assert (s["total_spent"], s["total_received"], s["net"], s["num_transactions"]) == (1000, 3000, 2000, 4)
    assert s["spend_by_category"][0] == {"category": "Food & Dining", "amount": 850.0, "share_pct": 85.0, "count": 2}
    assert s["weekly_spend"] == [{"week_starting": "2026-11-02", "amount": 800.0}, {"week_starting": "2026-11-09", "amount": 150.0}]
    assert s["daily_average_spend"] == 100 and s["small_spends"] == {"under": 200, "count": 2, "amount": 200.0}
    assert summarize(df, exclude_self=True)["total_spent"] == 950
    assert summarize(df.iloc[5:])["total_spent"] == 0
    json.dumps(s)

    assert ungrounded("₹1,000 and ₹849.80 but not ₹77", s) == ["77"]
    assert ungrounded("8 spends under ₹200, totalling ₹200.", s) == []
    text, bad = generate(s)  # the stub always cites ₹123,456: flagged after one retry
    assert bad == ["123,456"]


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
