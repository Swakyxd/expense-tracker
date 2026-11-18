# Implementation Plan — SMS Expense Tracker

> **Course:** Prompt Engineering — Class Project
> **Project:** An LLM-powered tracker that turns raw Indian bank/UPI SMS into categorized expenses, a spending dashboard and AI-written insights
> **Author:** Sayan Mahalik

---

## Table of Contents

1. [Problem Statement](#1-problem-statement)
2. [Objectives & Scope](#2-objectives--scope)
3. [System Architecture](#3-system-architecture)
4. [Tech Stack](#4-tech-stack)
5. [Project Structure](#5-project-structure)
6. [Data Model](#6-data-model)
7. [Pipeline Implementation](#7-pipeline-implementation)
8. [Prompt Design](#8-prompt-design)
9. [Streamlit Application](#9-streamlit-application)
10. [Evaluation Methodology](#10-evaluation-methodology)
11. [Edge Cases](#11-edge-cases)
12. [Privacy & Safety](#12-privacy--safety)
13. [Timeline](#13-timeline)
14. [Deliverables](#14-deliverables)
15. [Risks & Mitigations](#15-risks--mitigations)
16. [Future Work](#16-future-work)

---

## 1. Problem Statement

Most Indians make dozens of digital payments every month through UPI, cards, NEFT/IMPS and autopay. Each one triggers an SMS, but:

- Every bank and UPI app uses a **different SMS format**.
- Transaction SMS are buried among **OTPs, promos, KYC reminders and balance alerts**.
- Nobody adds these messages up by hand, so people **don't know where their money goes**.
- Existing apps often need bank logins or broad SMS permissions and send the data to third-party servers.

Regex-based parsers break whenever a bank changes its template. **LLMs can read messy, unseen formats**, but they need careful prompting to stay accurate, avoid making up values, and return machine-readable output.

**Goal:** design, iterate on and evaluate prompts that reliably turn raw SMS into structured financial data, and wrap them in a useful personal-finance tool.

---

## 2. Objectives & Scope

### 2.1 Objectives

| # | Objective | Success Criterion |
|---|-----------|-------------------|
| O1 | Separate transaction SMS from noise (OTP, promo, alerts) | Detection F1 ≥ 0.95 |
| O2 | Extract amount, type, merchant, date, mode, status | Amount accuracy ≥ 95%, overall field accuracy ≥ 90% |
| O3 | Assign each transaction to a spending category | Category accuracy ≥ 85% |
| O4 | Always produce valid structured output | Valid-JSON rate ≥ 99% (after repair) |
| O5 | Show measurable improvement across prompt versions | Report a v1 → v4 comparison table |
| O6 | Produce a usable dashboard with insights | Working Streamlit demo |

### 2.2 In Scope
- English-language SMS from major Indian banks (SBI, HDFC, ICICI, Axis, Kotak, PNB, BoB) and UPI apps (PhonePe, GPay, Paytm)
- Input by pasting text, or uploading `.txt` / `.csv` / Android *SMS Backup & Restore* `.xml`
- Four prompt versions compared on a labelled test set

### 2.3 Out of Scope
- Reading SMS directly from a phone (needs an Android app)
- Bank-statement PDFs
- SMS in Hindi or other regional languages (future work)
- Multi-user accounts / cloud storage

---

## 3. System Architecture

```
┌──────────────────────────┐
│  Raw SMS (paste/upload)  │
└────────────┬─────────────┘
             ▼
┌──────────────────────────┐   Python only, no LLM
│ [1] PREPROCESS           │   • noise filter (OTP/promo)
│                          │   • PII masking
│                          │   • dedupe
└────────────┬─────────────┘
             ▼
┌──────────────────────────┐   LLM call (batched, 10 SMS/call)
│ [2] EXTRACT              │   • strict JSON schema
│                          │   • rules + few-shot
└────────────┬─────────────┘
             ▼
┌──────────────────────────┐   Python
│ [3] VALIDATE & REPAIR    │   • Pydantic schema check
│                          │   • amount-grounding check
│                          │   • retry with error feedback (max 2)
└────────────┬─────────────┘
             ▼
┌──────────────────────────┐   Rules first → LLM fallback
│ [4] CATEGORIZE           │   • merchant dictionary
│                          │   • cached LLM classification
└────────────┬─────────────┘
             ▼
┌──────────────────────────┐   pandas, no LLM
│ [5] AGGREGATE            │   • totals, by category, by merchant,
│                          │     weekly trend, top spends
└────────────┬─────────────┘
             ▼
┌──────────────────────────┐   LLM call
│ [6] INSIGHTS             │   • gets ONLY computed numbers
│                          │   • writes observations + tips
└────────────┬─────────────┘
             ▼
┌──────────────────────────┐
│  Streamlit Dashboard     │
└──────────────────────────┘
```

### 3.1 Design Principles

1. **Use the LLM only where rules fail.** Filtering, masking, arithmetic and known-merchant categorization are deterministic, which makes them cheaper, faster and accurate.
2. **The LLM never does arithmetic.** Every total is computed in pandas, and the insights prompt is forbidden from computing new numbers.
3. **Ground every extracted value in the source text.** If an amount doesn't appear in the SMS, the row is flagged for review.
4. **Fail loudly, not silently.** Uncertain fields become `null`, and invalid rows show up in a "Needs review" table instead of being dropped.
5. **Privacy by default.** Account numbers, phone numbers and reference IDs are masked *before* any API call.

---

## 4. Tech Stack

| Layer | Tool | Reason |
|-------|------|--------|
| Language | Python 3.10+ | Ecosystem |
| LLM | Google Gemini Flash (free tier) via `google-genai` | Free, fast, supports `response_schema` for native JSON output |
| Validation | `pydantic` v2 | Enforces the schema and gives readable error messages to feed back for repair |
| Data | `pandas` | Aggregation |
| UI | `streamlit` | Dashboard in about 150 lines |
| Charts | `plotly` | Interactive charts inside Streamlit |
| Fuzzy matching | `rapidfuzz` | Merchant-name matching in eval and the rules engine |
| Config | `python-dotenv` | Keeps the API key out of the code |

> **Swappable LLM:** all calls go through one function in `pipeline/llm.py`, so OpenAI / Claude / Groq / a local Ollama model can replace Gemini by changing one file. Keep the model name in `.env` (`MODEL_NAME=...`) and use whichever Flash model the free tier currently offers.

**`requirements.txt`**
```
google-genai
pydantic>=2
pandas
streamlit
plotly
rapidfuzz
python-dotenv
matplotlib
```

---

## 5. Project Structure

```
sms-expense-tracker/
├── app.py                     # Streamlit UI
├── pipeline/
│   ├── __init__.py
│   ├── llm.py                 # single LLM wrapper (call, retries, token logging)
│   ├── preprocess.py          # filter, mask, dedupe, file parsers
│   ├── schema.py              # Pydantic models
│   ├── extract.py             # extraction + validation + repair loop
│   ├── categorize.py          # rules dictionary + LLM fallback + cache
│   ├── aggregate.py           # pandas summaries
│   └── insights.py            # insights prompt
├── prompts/
│   ├── extract_v1.txt         # zero-shot baseline
│   ├── extract_v2.txt         # + schema + rules
│   ├── extract_v3.txt         # + few-shot examples
│   ├── extract_v4.txt         # same as v3; repair loop enabled in code
│   ├── repair.txt
│   ├── categorize.txt
│   └── insights.txt
├── data/
│   ├── sample_sms.txt         # demo input
│   ├── test_sms.csv           # 60 labelled evaluation SMS
│   └── merchant_rules.json    # merchant → category dictionary
├── eval/
│   ├── run_eval.py            # runs v1–v4, writes results
│   ├── metrics.py
│   └── results/               # results.csv, charts, failure log
├── .env.example               # GEMINI_API_KEY=, MODEL_NAME=
├── requirements.txt
└── README.md
```

---

## 6. Data Model

### 6.1 Extraction Schema (`pipeline/schema.py`)

```python
from pydantic import BaseModel, Field
from typing import Literal, Optional

class Transaction(BaseModel):
    id: int
    is_transaction: bool
    type: Optional[Literal["debit", "credit"]] = None
    amount: Optional[float] = Field(default=None, gt=0)
    merchant: Optional[str] = None
    date: Optional[str] = None            # ISO YYYY-MM-DD
    mode: Optional[Literal["UPI", "CARD", "NEFT_IMPS", "ATM", "AUTOPAY", "OTHER"]] = None
    status: Optional[Literal["success", "failed", "reversed"]] = None
    account_last4: Optional[str] = None
```

**Validation rules on top of the schema:**
- If `is_transaction == True`, then `type`, `amount` and `status` are required.
- `date` must parse as a valid date and not be in the future.
- `amount` must appear in the raw SMS text (grounding check; see §7.3).

### 6.2 Enriched Record (after categorization)

| Field | Source |
|-------|--------|
| all extraction fields | LLM |
| `category` | rules / LLM |
| `category_source` | `"rule"` / `"llm"` / `"user"` |
| `needs_review` | validator |
| `raw_sms` | original (masked) text |

### 6.3 Categories (fixed list)

`Food & Dining` · `Groceries` · `Travel & Transport` · `Shopping` · `Bills & Recharges` · `Entertainment & Subscriptions` · `Health` · `Education` · `Rent & Housing` · `Transfers to People` · `Investments` · `Cash Withdrawal` · `Income` · `Refund` · `Other`

---

## 7. Pipeline Implementation

### 7.1 Step 1 — Preprocessing (`preprocess.py`)

**a) Input parsers**
- `.txt` / pasted text: split on blank lines; each block is one SMS
- `.csv`: read the `body` (and optional `date`, `sender`) columns
- `.xml` (*SMS Backup & Restore*): parse `<sms body="..." date="..." address="...">`. Keep the SMS timestamp; it's used when the message itself has no date.

**b) Noise filter (keyword + regex)**
```python
DROP = r"\b(otp|one[- ]time password|verification code|do not share|offer|cashback upto|"
       r"win |congratulations|pre-approved|loan approved|kyc|click here to)\b"
KEEP_VERB = r"\b(debited|credited|spent|sent|received|withdrawn|paid|transferred|"
            r"refund(ed)?|reversed|declined|failed)\b"
AMOUNT = r"(rs\.?|inr|₹)\s?[\d,]+(\.\d{1,2})?"
```
Keep an SMS if it matches `AMOUNT` **and** `KEEP_VERB` and does not match `DROP`.

> In the eval, the filter is **switchable** so you can measure how much it saves in API calls and how many real transactions it wrongly drops.

**c) PII masking**
| Pattern | Replacement |
|---------|-------------|
| Account/card numbers (`XX1234`, `A/c *1234`, `ending 1234`, 9–18 digit runs) | keep last 4 → `XX1234` |
| UPI reference / RRN numbers (12-digit) | `[REF]` |
| Phone numbers (10-digit starting 6–9) | `[PHONE]` |
| Email addresses | `[EMAIL]` |

**d) Deduplication**
Two SMS are duplicates if they have the same amount, the same reference number (checked before masking), and arrive within 5 minutes of each other.

### 7.2 Step 2 — Extraction (`extract.py`)

- Batch **10 SMS per call**, each prefixed with an `id`.
- Use Gemini `response_mime_type="application/json"` + `response_schema` (Transaction list).
- `temperature = 0` for repeatable output.
- Log `prompt_tokens`, `output_tokens` and latency for every call.

```python
def extract_batch(sms_batch, prompt_version):
    prompt = load_prompt(f"extract_{prompt_version}.txt")
    user_msg = "\n".join(f"[{s.id}] {s.text}" for s in sms_batch)
    raw = llm.call(system=prompt, user=user_msg, json_schema=TransactionList)
    return validate_and_repair(raw, sms_batch, enabled=(prompt_version == "v4"))
```

### 7.3 Step 3 — Validation & Repair

```
for each batch output:
    try Pydantic parse
    run semantic checks:
        • required fields present when is_transaction
        • date parseable, not in future
        • amount grounded in raw SMS (normalize "1,249.00" → 1249.0 and search)
    if errors and retries < 2:
        send repair prompt with {original SMS, previous output, error list}
    else if still invalid:
        mark needs_review = True (never silently drop)
```

**Amount-grounding check:** take every number in the raw SMS (removing commas) and check that the extracted amount matches one of them. This catches made-up amounts and confusion with the balance in some cases. (Balance confusion is caught by the rules and few-shot examples, and measured in eval.)

### 7.4 Step 4 — Categorization (`categorize.py`)

1. **Rules:** `merchant_rules.json` with about 80 entries, matched case-insensitively with a fuzzy threshold of 85:
   ```json
   {
     "Food & Dining": ["swiggy", "zomato", "dominos", "mcdonalds", "kfc", "starbucks", "eatsure"],
     "Groceries": ["blinkit", "zepto", "bigbasket", "dmart", "instamart", "jiomart"],
     "Travel & Transport": ["uber", "ola", "rapido", "irctc", "redbus", "makemytrip", "indigo", "fastag", "metro"],
     "Shopping": ["amazon", "flipkart", "myntra", "ajio", "meesho", "nykaa"],
     "Bills & Recharges": ["jio", "airtel", "vi ", "bsnl", "electricity", "bescom", "tata power", "act fibernet"],
     "Entertainment & Subscriptions": ["netflix", "spotify", "hotstar", "prime video", "bookmyshow", "youtube"],
     "Health": ["apollo", "pharmeasy", "1mg", "netmeds", "practo"],
     "Investments": ["zerodha", "groww", "upstox", "sip", "mutual fund"],
     "Education": ["coursera", "udemy", "unacademy", "college", "university"]
   }
   ```
2. **Mode/type rules:** `mode == ATM` → Cash Withdrawal; `type == credit` + "salary" → Income; refund keywords → Refund.
3. **LLM fallback** for unmatched merchants: send unique merchant names in one batched call (`categorize.txt`).
4. **Cache** results in a dictionary (and `cache.json`) so each merchant is classified only once.
5. Users can override a category in the UI → `category_source = "user"`.

### 7.5 Step 5 — Aggregation (`aggregate.py`)

Only rows where `is_transaction and status == "success"` are counted.

| Metric | Computation |
|--------|-------------|
| Total spent / received / net | sum of debits / credits |
| Spend by category | groupby category (debits only), % share |
| Top 5 merchants | groupby merchant, sum + count |
| Weekly trend | resample by week |
| Largest 5 transactions | sort by amount |
| Small frequent spends | count & sum of debits < ₹200 |
| Daily average spend | total spent / days in range |

Output: one `summary` dict, which is used by both the UI and the insights prompt.

### 7.6 Step 6 — Insights (`insights.py`)

- Input: **only** the `summary` JSON (no raw SMS, no PII).
- Output: 3 observations + 2 saving tips, under 120 words.
- A post-check confirms every ₹ number in the output exists in the summary; if not, regenerate once.

---

## 8. Prompt Design

### 8.1 Version Ladder

| Version | Technique Added | Hypothesis |
|---------|----------------|------------|
| **v1** | Zero-shot instruction | Baseline; expect wrong amounts (balance vs amount), promos counted as transactions, inconsistent JSON |
| **v2** | + Role + explicit schema + domain rules | Fixes structure and the common confusions |
| **v3** | + 6 few-shot examples of hard cases | Fixes edge cases: failed, refund, autopay, P2P |
| **v4** | v3 + validation & self-repair loop | Pushes valid-output rate close to 100% and catches made-up values |

### 8.2 `extract_v1.txt` — Baseline

```
Extract the transaction details from each SMS below and return JSON.
```

### 8.3 `extract_v2.txt` — Role + Schema + Rules

```
You are a precise financial SMS parser for Indian bank, card and UPI messages.

For EACH message (identified by [id]) return one JSON object with these fields:
- id: the message id
- is_transaction: true only if money actually moved or was attempted
- type: "debit" (money left the user's account) or "credit" (money came in)
- amount: the transaction amount as a number
- merchant: who the user paid or received money from
- date: YYYY-MM-DD
- mode: UPI | CARD | NEFT_IMPS | ATM | AUTOPAY | OTHER
- status: success | failed | reversed
- account_last4: last 4 digits of the user's account/card if present

RULES
1. amount is the transaction amount, NEVER the available/remaining balance.
2. "debited from A/c ... credited to VPA xyz@bank" means the user PAID xyz → type = debit, merchant = xyz.
3. OTPs, promotional offers, KYC reminders, loan offers and pure balance alerts → is_transaction = false, other fields null.
4. Mandate / autopay SETUP or upcoming-payment reminders are NOT transactions. An actual autopay deduction IS a transaction (mode = AUTOPAY).
5. Words like "failed", "declined", "unsuccessful" → status = failed. "Reversed", "refunded to your account" for a failed payment → status = reversed.
6. A refund from a merchant is a credit with status = success.
7. Dates: convert DD-MM-YY, DD-Mon-YY, DD/MM/YYYY etc. to YYYY-MM-DD. If the year is missing, use {current_year}.
8. merchant: return a clean, human-readable name. "SWIGGY*BANGALORE ORD" → "Swiggy", "zomato-order@ptybl" → "Zomato". For person-to-person UPI, return the person's name if shown, otherwise the VPA.
9. If a field cannot be determined from the text, return null. NEVER guess or invent values.
10. Return ONLY a JSON array — no explanations, no markdown.
```

### 8.4 `extract_v3.txt` — v2 + Few-Shot Examples

Add this block after the rules. These six examples are chosen to cover the **most frequent failure modes seen in v2**. Update them after the first eval run, using real mistakes.

```
EXAMPLES

[101] Dear UPI user A/C X4521 debited by 249.00 on date 12Nov26 trf to SWIGGY Refno 431622819023. If not u? call 1800111109. -SBI
→ {"id":101,"is_transaction":true,"type":"debit","amount":249.0,"merchant":"Swiggy","date":"2026-11-12","mode":"UPI","status":"success","account_last4":"4521"}

[102] Rs.1,850.00 spent on HDFC Bank Card x7788 at AMAZON PAY INDIA on 2026-11-10:19:42:11. Avl Lmt: Rs.48,150.00. Not you? Call 18002586161
→ {"id":102,"is_transaction":true,"type":"debit","amount":1850.0,"merchant":"Amazon","date":"2026-11-10","mode":"CARD","status":"success","account_last4":"7788"}

[103] Your a/c no. XXXXXXXX3390 is credited by Rs.45,000.00 on 01-11-26 by a/c linked to ACME TECH PVT LTD (NEFT). Avl bal Rs.52,310.40 -ICICI Bank
→ {"id":103,"is_transaction":true,"type":"credit","amount":45000.0,"merchant":"ACME Tech Pvt Ltd","date":"2026-11-01","mode":"NEFT_IMPS","status":"success","account_last4":"3390"}

[104] Your UPI transaction of Rs 560.00 to rapido@ybl has FAILED. Amount if debited will be refunded within 3 working days. -Axis Bank
→ {"id":104,"is_transaction":true,"type":"debit","amount":560.0,"merchant":"Rapido","date":null,"mode":"UPI","status":"failed","account_last4":null}

[105] Refund of Rs.799.00 from MYNTRA has been credited to your Kotak Bank A/c X2210 on 08/11/2026. Avl Bal: Rs 12,004.55
→ {"id":105,"is_transaction":true,"type":"credit","amount":799.0,"merchant":"Myntra","date":"2026-11-08","mode":"OTHER","status":"success","account_last4":"2210"}

[106] Reminder: Your e-mandate for NETFLIX of Rs.199.00 will be debited on 20-Nov-26 from A/c XX6612. To cancel visit your bank app.
→ {"id":106,"is_transaction":false,"type":null,"amount":null,"merchant":null,"date":null,"mode":null,"status":null,"account_last4":null}
```

### 8.5 `extract_v4` — v3 + Repair Loop

The prompt text is the same as v3; the difference is in the code (§7.3). Repair prompt (`repair.txt`):

```
Your previous output for the SMS below failed validation.

SMS:
[{id}] {sms_text}

Your previous output:
{previous_json}

Errors:
{error_list}

Re-read the SMS carefully and return a corrected JSON object for this message only.
Follow all original rules. If a value is not present in the SMS, use null.
Return ONLY the JSON object.
```

### 8.6 `categorize.txt`

```
Classify each merchant name into exactly ONE category from this list:
Food & Dining, Groceries, Travel & Transport, Shopping, Bills & Recharges,
Entertainment & Subscriptions, Health, Education, Rent & Housing,
Transfers to People, Investments, Cash Withdrawal, Income, Refund, Other

Rules:
- A person's name or a personal UPI ID (e.g. "rahul.k@okaxis", "Priya Sharma") → Transfers to People.
- If you are not reasonably sure, choose "Other". Do not invent new categories.
- Indian context: e.g. "Blinkit" = Groceries, "BESCOM" = Bills & Recharges, "Rapido" = Travel & Transport.

Return a JSON object mapping each merchant to its category, e.g.
{"Swiggy": "Food & Dining", "rahul.k@okaxis": "Transfers to People"}
```

### 8.7 `insights.txt`

```
You are a friendly personal-finance assistant for an Indian college student.

Below is a JSON summary of their spending, already calculated:
{summary_json}

Write:
1. Three short observations about their spending patterns.
2. Two practical, specific tips to save money.

Rules:
- Use ONLY numbers that appear in the summary. Do NOT calculate new totals or percentages.
- Use ₹ and Indian number formatting (e.g. ₹12,450).
- Be specific (name categories/merchants), encouraging, not preachy.
- Maximum 120 words. Use bullet points.
```

### 8.8 Prompt-Engineering Techniques Demonstrated

| Technique | Where |
|-----------|-------|
| Role prompting | v2+, insights |
| Explicit output schema / structured output | v2+, enforced by `response_schema` |
| Rule-based constraints | v2+ rules list |
| Few-shot learning with hard cases | v3+ |
| Choosing examples based on errors | v3 examples come from v2 failures |
| Self-correction / repair loop with error feedback | v4 |
| Grounding & anti-hallucination checks | amount check, insights number check |
| Abstention (`null` / "Other") | all prompts |
| Batching for cost efficiency | 10 SMS/call |
| Hybrid rules + LLM routing | categorization |
| Prompt chaining | extract → categorize → insights |

---

## 9. Streamlit Application

### 9.1 Layout

```
┌───────────── Sidebar ─────────────┐┌──────────────── Main ─────────────────┐
│ 📥 Input                          ││  KPI cards:                           │
│  ○ Paste SMS  ○ Upload file       ││  [Spent] [Received] [Net] [# Txns]    │
│  [ text area / file uploader ]    ││                                       │
│  [Load sample data]               ││  📋 Transactions (editable table)     │
│                                   ││     – change category inline          │
│ ⚙️ Settings                       ││  ⚠️ Needs review (expander)           │
│  Prompt version: v1/v2/v3/v4      ││                                       │
│  [x] Pre-filter noise             ││  🥧 Spend by category  📊 Weekly trend│
│                                   ││  🏪 Top merchants      💸 Top spends  │
│  [ ▶ Analyze ]                    ││                                       │
│                                   ││  💡 AI Insights                       │
│ Stats: SMS in / filtered / API    ││                                       │
│ calls / tokens                    ││  [⬇ Download CSV]                     │
└───────────────────────────────────┘└───────────────────────────────────────┘
```

### 9.2 Key Implementation Notes
- Use `st.session_state` to keep results so editing a category doesn't re-run the LLM.
- `st.data_editor` with a `SelectboxColumn` for category overrides; aggregation re-runs on edit.
- `st.cache_data` on the extraction function, keyed on (SMS text, prompt version).
- Showing the prompt-version selector in the UI lets you **demo v1 vs v4 live**, which works well in a presentation.
- A spinner + progress bar per batch.

---

## 10. Evaluation Methodology

### 10.1 Test Dataset (`data/test_sms.csv`)

**60 synthetic SMS** modelled on real bank templates (no personal data):

| Group | Count | Examples |
|-------|-------|----------|
| UPI debits | 14 | SBI, HDFC, PhonePe/GPay style, P2P and merchant |
| Card spends | 6 | HDFC, ICICI, Axis credit/debit card |
| Credits | 6 | salary NEFT, UPI received, interest credit |
| ATM withdrawals | 3 | |
| Autopay deductions | 3 | Netflix, Spotify, SIP |
| Refunds | 3 | |
| Failed / reversed | 5 | |
| **Hard negatives** | **20** | OTPs (5), promos (5), autopay/mandate reminders (3), balance alerts (3), card bill due reminders (2), loan offers (2) |

**Columns:** `id, sms, is_transaction, type, amount, merchant, date, mode, status, category`

**Labelling:** done by hand. Double-check the 10 hardest rows a second time.

**Split:** the six few-shot examples are *not* in the test set (to avoid leakage).

### 10.2 Metrics (`eval/metrics.py`)

| Metric | Definition |
|--------|------------|
| Detection Precision / Recall / F1 | on `is_transaction` |
| Amount accuracy | exact match (±0.01) on true transactions |
| Type accuracy | exact match |
| Date accuracy | exact ISO match (null-vs-null counts as correct) |
| Merchant accuracy | `rapidfuzz.ratio ≥ 80` against the label |
| Status accuracy | exact match |
| Category accuracy | exact match (after the full pipeline) |
| Overall field accuracy | mean of the field accuracies above |
| Valid-JSON rate | % of batches that parse on the first try |
| Avg. repairs per batch | v4 only |
| Tokens per SMS / latency per SMS | cost and speed |

### 10.3 Experiments

| Exp | Description |
|-----|-------------|
| E1 | **Prompt ablation:** v1 vs v2 vs v3 vs v4 on all metrics (main result) |
| E2 | **Pre-filter on vs off:** API calls saved vs real transactions wrongly dropped |
| E3 | **Batch size:** 1 vs 10 vs 30 SMS per call → accuracy vs tokens |
| E4 | **Categorization:** rules-only vs LLM-only vs hybrid |
| E5 *(optional)* | **Model comparison:** Gemini Flash vs one other free model (e.g. Groq Llama) using the v4 prompt |

Run each configuration **3 times** at temperature 0 and report the mean. Note any differences between runs.

### 10.4 Outputs (`eval/results/`)
- `results.csv`: one row per (experiment, configuration, metric)
- `ablation_chart.png`: grouped bar chart of field accuracy by prompt version
- `failure_log.md`: every wrong prediction with the SMS, expected value, predicted value and the likely cause
- 3 hand-picked **before/after** examples for the report (e.g. v1 reads the balance as the amount → v3 gets it right)

### 10.5 Expected Results (hypothesis, to be replaced with real numbers)

| Metric | v1 | v2 | v3 | v4 |
|--------|----|----|----|----|
| Detection F1 | ~0.80 | ~0.92 | ~0.96 | ~0.97 |
| Amount acc. | ~85% | ~93% | ~97% | ~98% |
| Status acc. | ~70% | ~85% | ~95% | ~95% |
| Valid JSON | ~90% | ~98% | ~98% | ~100% |

---

## 11. Edge Cases

| # | Case | Example Signal | Expected Handling |
|---|------|----------------|-------------------|
| 1 | Balance shown next to amount | "Avl Bal Rs.12,004" | amount ≠ balance (rule 1 + example 102/103) |
| 2 | "credited to VPA" inside a debit SMS | "debited … credited to xyz@ybl" | type = debit (rule 2) |
| 3 | Failed payment | "FAILED", "declined" | status = failed, excluded from totals |
| 4 | Reversal of a failed payment | "reversed to your a/c" | status = reversed, excluded from totals |
| 5 | Merchant refund | "Refund of Rs…" | credit, category = Refund |
| 6 | Mandate reminder | "will be debited on" | not a transaction |
| 7 | Actual autopay | "debited towards NACH/mandate" | debit, mode = AUTOPAY |
| 8 | Credit card bill reminder | "Total amt due" | not a transaction |
| 9 | Credit card bill payment | "payment of Rs… received towards card" | transaction; flag as a self-transfer so it isn't counted twice |
| 10 | Self-transfer between own accounts | same name / "to own a/c" | category = Transfers, can be excluded via toggle |
| 11 | Amount formats | `Rs.1,249.00`, `INR 1249`, `₹1,249` | → 1249.0 |
| 12 | Date formats | `12Nov26`, `12-11-26`, `2026-11-12:19:42`, `12/11/2026` | → `2026-11-12` |
| 13 | Missing date | none in text | use SMS timestamp from backup file, else null |
| 14 | Duplicate SMS (bank + UPI app) | same amount + ref | dedupe |
| 15 | Cryptic merchant | "PYU*ZOMATOONLINE", "BHARATPE MERCH" | clean name; fallback "Other" |
| 16 | P2P payment | "to RAHUL KUMAR" | merchant = person, category = Transfers to People |
| 17 | Cashback credit | "cashback of Rs 25 credited" | credit, category = Income/Refund |
| 18 | Multiple amounts (EMI, fee + amount) | | pick the transaction amount; flag if ambiguous |

---

## 12. Privacy & Safety

- **Masking before the API:** account numbers, references, phone numbers and emails are masked in `preprocess.py`; the LLM never sees full identifiers.
- **Insights prompt** gets only aggregated numbers, never raw SMS.
- **No storage:** data lives only in the Streamlit session; nothing is written to disk except an optional user-triggered CSV download.
- **Synthetic eval data:** the submitted dataset contains no real personal information.
- **API key** is kept in `.env` (git-ignored); `.env.example` is committed instead.
- **Disclaimer in the UI:** "Not financial advice. Please verify transactions flagged for review."
- **Local-model option** (Ollama) is listed as future work for fully offline use.

---

## 13. Timeline (submission tomorrow)

| Time | Task | Output |
|------|------|--------|
| 22:15 – 22:45 | Project setup, `llm.py`, `schema.py`, API key test | Hello-world LLM call returning JSON |
| 22:45 – 23:30 | Write 60 test SMS + labels; `sample_sms.txt` | `test_sms.csv` |
| 23:30 – 00:00 | `preprocess.py` (filter, mask, dedupe, parsers) | Filtered, masked SMS list |
| 00:00 – 00:45 | Extraction prompts v1–v3, `extract.py`, repair loop (v4) | Working extraction |
| 00:45 – 01:15 | `categorize.py`, `aggregate.py`, `insights.py` | Full pipeline end-to-end |
| 01:15 – 02:00 | `run_eval.py` + metrics; run E1 (E2–E4 if time) | `results.csv`, charts, failure log |
| 02:00 – 02:15 | Update v3 few-shot examples from real v2 failures; re-run | Final numbers |
| 02:15 – 03:00 | `app.py` Streamlit dashboard | Working demo |
| 03:00 – 03:45 | Report / slides + screenshots + README | Submission package |
| 03:45 – 04:00 | Final test run from a clean environment | ✅ |

**Fallback if time runs short:** skip E3–E5, skip the XML parser and the insights post-check. E1 (the prompt ablation) and a working demo are the must-haves.

---

## 14. Deliverables

1. **Code repository** (structure in §5) with a README covering setup, run and eval instructions
2. **Streamlit demo** (`streamlit run app.py`)
3. **Evaluation results:** tables, charts, failure log
4. **Project report** with these sections:
   1. Introduction & problem statement
   2. Related work (regex SMS parsers, existing expense apps, LLM information extraction)
   3. System architecture
   4. Prompt design & iteration (v1 → v4 side-by-side with reasoning)
   5. Experimental setup (dataset, metrics)
   6. Results & analysis (ablation table, charts, before/after examples)
   7. Error analysis (remaining failure categories)
   8. Privacy, limitations & ethics
   9. Conclusion & future work
5. **Presentation / demo script (≈5 min):** problem (30s) → architecture (45s) → prompt evolution with examples (90s) → results chart (60s) → live demo: paste messy SMS → dashboard → insights (60s) → takeaways (15s)

---

## 15. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Free-tier rate limit / quota hit | Eval stalls | Batch 10/call, cache responses to disk, `time.sleep` + exponential backoff, keep the eval set at 60 |
| API outage during demo | Demo fails | Pre-computed results cached; "Load sample results" button works offline |
| LLM output varies between runs | Inconsistent numbers | temperature 0, 3 runs, report the mean |
| Labelling mistakes in test set | Wrong metrics | Double-check hard cases; review the failure log for label errors |
| Few-shot examples leak into test set | Inflated v3 scores | Keep the example SMS separate from `test_sms.csv` |
| Time overrun | Incomplete submission | Follow the fallback in §13; finish E1 + demo first |

---

## 16. Future Work

- **Android app** that reads SMS on the device (with permission) and syncs automatically
- **On-device / local LLM** (Ollama, small quantized model) for full privacy
- **Budgets & alerts:** "You've used 80% of your food budget"
- **Hindi and regional-language SMS** support
- **Recurring payment detection:** subscriptions you forgot about
- **Bank-statement PDF** import to cross-check SMS data
- **Fine-tuning a small model** on labelled SMS and comparing it with prompt-only approaches
