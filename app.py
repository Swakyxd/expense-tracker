"""Streamlit dashboard: streamlit run app.py"""
import json
import re
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from pipeline import llm
from pipeline.aggregate import summarize
from pipeline.categorize import categorize
from pipeline.extract import batches, extract_batch
from pipeline.insights import generate
from pipeline.preprocess import parse_csv, parse_text, parse_xml, preprocess
from pipeline.schema import CATEGORIES

DATA = Path(__file__).parent / "data"
SAMPLE = (DATA / "sample_sms.txt").read_text(encoding="utf-8")
SAMPLE_RESULTS = DATA / "sample_results.json"  # written after a live run on the sample; lets the demo work offline
BLUE = "#2a78d6"

st.set_page_config("SMS Expense Tracker", "💸", layout="wide")


def inr(x: float) -> str:
    """₹ with Indian digit grouping: 1245000 → ₹12,45,000."""
    digits = f"{abs(x):.0f}"
    head, tail = digits[:-3], digits[-3:]
    if head:
        tail = re.sub(r"(?<=\d)(?=(\d\d)+$)", ",", head) + "," + tail
    return ("-" if x < 0 else "") + "₹" + tail


@st.cache_data(show_spinner=False)
def cached_extract(batch: tuple, version: str):
    return extract_batch(list(batch), version)[0]


def analyze(messages, version, use_filter, exclude_self, is_sample):
    kept, noise, duplicates = preprocess(messages, use_filter)
    first_call = len(llm.STATS)
    rows, chunks = [], list(batches(kept))
    bar = st.progress(0.0, "Extracting…")
    try:
        for i, batch in enumerate(chunks, 1):
            rows += cached_extract(tuple(batch), version)
            bar.progress(i / len(chunks), f"Extracted batch {i} of {len(chunks)}")
    finally:
        bar.empty()
    if not rows:
        st.warning("No transaction SMS found in the input.")
        return
    with st.spinner("Categorizing and writing insights…"):
        categorize(rows)
        insights = generate(summarize(pd.DataFrame(rows), exclude_self))
    calls = llm.STATS[first_call:]
    result = {
        "rows": rows, "noise": [m.text for m in noise], "insights": insights,
        "stats": {"SMS in": len(messages), "Filtered as noise": len(noise), "Duplicates removed": duplicates,
                  "API calls": len(calls), "Tokens": sum(c["prompt_tokens"] + c["output_tokens"] for c in calls)},
    }
    if is_sample:
        SAMPLE_RESULTS.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    show(result)


def show(result: dict):
    st.session_state.result = result
    st.session_state.run_id = st.session_state.get("run_id", 0) + 1  # resets the category editor


def bar_chart(data: pd.DataFrame, category: str, horizontal: bool):
    x, y = ("amount", category) if horizontal else (category, "amount")
    fig = px.bar(data, x=x, y=y, orientation="h" if horizontal else "v", text="label", color_discrete_sequence=[BLUE])
    fig.update_traces(marker_cornerradius=4, textposition="outside", cliponaxis=False,
                      hovertemplate=f"%{{{'y' if horizontal else 'x'}}}<br>%{{text}}<extra></extra>")
    fig.update_layout(height=max(220, 44 * len(data) + 60) if horizontal else 320, bargap=0.45,
                      margin=dict(l=0, r=90 if horizontal else 0, t=24, b=0), xaxis_title=None, yaxis_title=None)
    value_axis = fig.update_xaxes if horizontal else fig.update_yaxes
    value_axis(showticklabels=False, showgrid=False, zeroline=False)  # every bar carries its value
    if horizontal:
        fig.update_yaxes(autorange="reversed")  # largest on top
    else:
        fig.update_xaxes(type="category")
    st.plotly_chart(fig, width="stretch")


# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("📥 Input")
    source = st.radio("Source", ["Paste SMS", "Upload file"], horizontal=True, label_visibility="collapsed")
    text, upload = "", None
    if source == "Paste SMS":
        text = st.text_area("SMS messages", key="sms_text", height=200,
                            placeholder="Paste SMS here, with a blank line between messages (or one per line).")
        st.button("Load sample data", on_click=lambda: st.session_state.update(sms_text=SAMPLE))
    else:
        upload = st.file_uploader("File", type=["txt", "csv", "xml"], label_visibility="collapsed",
                                  help=".txt, .csv with a 'body' column, or an SMS Backup & Restore .xml")

    st.header("⚙️ Settings")
    version = st.selectbox("Prompt version", ["v4", "v3", "v2", "v1"],
                           help="v1 zero-shot · v2 + role, schema, rules · v3 + few-shot · v4 + repair loop")
    use_filter = st.checkbox("Pre-filter noise", True, help="Drop OTPs, promos and alerts with rules before calling the LLM")
    exclude_self = st.checkbox("Exclude self-transfers", True, help="Leave own-account moves and card bill payments out of the totals")
    run = st.button("▶ Analyze", type="primary", width="stretch")
    if SAMPLE_RESULTS.exists():
        st.button("Load sample results (offline)", width="stretch",
                  on_click=lambda: show(json.loads(SAMPLE_RESULTS.read_text(encoding="utf-8"))))

st.title("💸 SMS Expense Tracker")

if run:
    try:
        if upload is None:
            messages = parse_text(text)
        elif upload.name.lower().endswith(".csv"):
            messages = parse_csv(upload)
        elif upload.name.lower().endswith(".xml"):
            messages = parse_xml(upload)
        else:
            messages = parse_text(upload.getvalue().decode("utf-8", errors="replace"))
        if messages:
            analyze(messages, version, use_filter, exclude_self, is_sample=text.strip() == SAMPLE.strip())
        else:
            st.warning("Paste some SMS or upload a file first.")
    except Exception as e:  # bad file, missing API key, quota: show it instead of a stack trace
        st.error(f"{type(e).__name__}: {e}")

if "result" not in st.session_state:
    st.info("Paste bank / UPI SMS in the sidebar (or load the sample data), then press **Analyze**.")
    st.stop()

result = st.session_state.result
with st.sidebar:
    st.header("📊 Run stats")
    st.caption("  \n".join(f"{k}: **{v:,}**" for k, v in result["stats"].items()))

# ── Transactions (category is editable; everything below recomputes from the edit) ───
df = pd.DataFrame(result["rows"])
txns = df[df["is_transaction"]]
columns = ["date", "merchant", "type", "amount", "category", "mode", "status", "needs_review", "raw_sms"]
kpis = st.container()
st.subheader("📋 Transactions")
edited = st.data_editor(
    txns[columns], key=f"editor_{st.session_state.run_id}", hide_index=True, width="stretch",
    disabled=[c for c in columns if c != "category"],
    column_config={
        "category": st.column_config.SelectboxColumn("category ✏️", options=CATEGORIES, required=True),
        "amount": st.column_config.NumberColumn(format="₹%.2f"),
        "needs_review": st.column_config.CheckboxColumn("⚠️ review"),
        "raw_sms": st.column_config.TextColumn("SMS (masked)", width="large"),
    })
changed = edited["category"] != txns["category"]
df.loc[txns.index, "category"] = edited["category"]
df.loc[changed[changed].index, "category_source"] = "user"

review = df[df["needs_review"]]
if len(review):
    with st.expander(f"⚠️ Needs review ({len(review)})", expanded=True):
        st.dataframe(review[["errors", "amount", "merchant", "date", "status", "raw_sms"]], hide_index=True, width="stretch")
if result["noise"]:
    with st.expander(f"🔇 Filtered out as noise ({len(result['noise'])})"):
        st.dataframe(pd.DataFrame({"SMS (masked)": result["noise"]}), hide_index=True, width="stretch")

# ── KPIs (rendered above the table) and charts ──────────────────────────────────────────────────────────
summary = summarize(df, exclude_self)
k1, k2, k3, k4 = kpis.columns(4)
k1.metric("Spent", inr(summary["total_spent"]))
k2.metric("Received", inr(summary["total_received"]))
k3.metric("Net", inr(summary["net"]))
k4.metric("Transactions", summary["num_transactions"])

if summary["total_spent"]:
    left, right = st.columns(2)
    with left:
        st.subheader("Spend by category")
        by_category = pd.DataFrame(summary["spend_by_category"])
        by_category["label"] = [f"{inr(a)} · {p:.0f}%" for a, p in zip(by_category["amount"], by_category["share_pct"])]
        bar_chart(by_category, "category", horizontal=True)
        st.subheader("Top merchants")
        merchants = pd.DataFrame(summary["top_merchants"])
        if len(merchants):
            merchants["label"] = [f"{inr(a)} · {c}×" for a, c in zip(merchants["amount"], merchants["count"])]
            bar_chart(merchants, "merchant", horizontal=True)
    with right:
        st.subheader("Weekly spend")
        weekly = pd.DataFrame(summary["weekly_spend"])
        if len(weekly):
            weekly["week"] = pd.to_datetime(weekly["week_starting"]).dt.strftime("%d %b %y")
            weekly["label"] = weekly["amount"].map(inr)
            bar_chart(weekly, "week", horizontal=False)
            st.caption(f"Week starting Monday · daily average {inr(summary['daily_average_spend'])} · "
                       f"{summary['small_spends']['count']} spends under ₹200 "
                       f"totalling {inr(summary['small_spends']['amount'])}")
        st.subheader("Largest spends")
        st.dataframe(pd.DataFrame(summary["largest_transactions"]), hide_index=True, width="stretch",
                     column_config={"amount": st.column_config.NumberColumn(format="₹%.2f")})

# ── Insights ─────────────────────────────────────────────────────────────────
st.subheader("💡 AI insights")
if st.button("Regenerate from current table"):
    try:
        with st.spinner("Writing insights…"):
            result["insights"] = generate(summary)
    except Exception as e:
        st.error(f"{type(e).__name__}: {e}")
insight_text, unverified = result["insights"]
st.markdown(insight_text.replace("$", "\\$"))
if unverified:
    st.warning("These figures in the insights are not in the computed summary, treat them with care: "
               + ", ".join("₹" + u for u in unverified))

st.download_button("⬇ Download CSV", df[df["is_transaction"]].drop(columns=["errors"]).to_csv(index=False),
                   "expenses.csv", "text/csv")
st.caption("Not financial advice. Please verify transactions flagged for review. "
           "Account numbers, references, phone numbers and emails are masked before anything is sent to the LLM.")
