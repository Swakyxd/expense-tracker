"""Step 5: every number the UI and the insights prompt show is computed here, in pandas."""
import pandas as pd


def _r(x) -> float:
    return round(float(x), 2)


def summarize(df: pd.DataFrame, exclude_self: bool = False) -> dict:
    """Counts only successful transactions. Returns a JSON-serialisable summary."""
    ok = df[df["is_transaction"].astype(bool) & (df["status"] == "success") & df["amount"].notna()]
    if exclude_self:
        ok = ok[~ok["self_transfer"].astype(bool)]
    debits, credits = ok[ok["type"] == "debit"], ok[ok["type"] == "credit"]
    spent, received = debits["amount"].sum(), credits["amount"].sum()

    by_cat = debits.groupby("category")["amount"].agg(["sum", "count"]).sort_values("sum", ascending=False)
    by_merchant = debits.groupby("merchant")["amount"].agg(["sum", "count"]).sort_values("sum", ascending=False).head(5)
    dated = debits.assign(date=pd.to_datetime(debits["date"], errors="coerce")).dropna(subset=["date"])
    weekly = dated.set_index("date")["amount"].resample("W-MON", label="left", closed="left").sum()
    weekly = weekly[weekly > 0]
    days = (dated["date"].max() - dated["date"].min()).days + 1 if len(dated) else 0
    small = debits[debits["amount"] < 200]

    return {
        "total_spent": _r(spent),
        "total_received": _r(received),
        "net": _r(received - spent),
        "num_transactions": int(len(ok)),
        "date_range": [dated["date"].min().date().isoformat(), dated["date"].max().date().isoformat()] if days else None,
        "daily_average_spend": _r(spent / days) if days else None,
        "spend_by_category": [
            {"category": c, "amount": _r(r["sum"]), "share_pct": _r(100 * r["sum"] / spent), "count": int(r["count"])}
            for c, r in by_cat.iterrows()],
        "top_merchants": [{"merchant": m, "amount": _r(r["sum"]), "count": int(r["count"])} for m, r in by_merchant.iterrows()],
        "weekly_spend": [{"week_starting": d.date().isoformat(), "amount": _r(a)} for d, a in weekly.items()],
        "largest_transactions": [
            {"date": r["date"], "merchant": r["merchant"], "amount": _r(r["amount"]), "category": r["category"]}
            for _, r in debits.nlargest(5, "amount").iterrows()],
        "small_spends": {"under": 200, "count": int(len(small)), "amount": _r(small["amount"].sum())},
    }
