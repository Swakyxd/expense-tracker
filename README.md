# SMS Expense Tracker

Turns raw Indian bank / UPI SMS into categorized expenses, a spending dashboard and AI-written insights.
Prompt Engineering class project. The full design is in [implementation_plan.md](implementation_plan.md).

```
raw SMS → preprocess (filter, dedupe, mask PII) → LLM extraction (batched, JSON schema)
        → validate + repair → categorize (rules, then LLM) → aggregate (pandas) → LLM insights → dashboard
```

The LLM is used only where rules fail: it reads the messages and writes the insights. Filtering, masking,
arithmetic and known-merchant categorization are plain Python.

## Setup

Needs Python 3.10+ and a free Gemini API key from <https://aistudio.google.com/apikey>.

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then put your key in GEMINI_API_KEY
```

`MODEL_NAME` in `.env` picks the model (default `gemini-3.5-flash`).

**Free-tier quota:** the free tier allows 20 requests per day per model (checked November 2026). One
Analyze on the sample data is 4 requests, and each eval experiment is 2 to 12. `gemini-3.5-flash`,
`gemini-3.5-flash-lite` and `gemini-4-hydrogen` all worked and have separate quotas, so switching `MODEL_NAME`
gives you another 20. (`gemini-3.7-flash` and `gemini-3.8-flash` timed out; `gemini-3.1-flash-lite` works but is slow.)

## Run the dashboard

```bash
streamlit run app.py
```

Click **Load sample data**, then **Analyze**. You can also paste your own SMS (blank line between messages)
or upload a `.txt`, a `.csv` with a `body` column, or an Android *SMS Backup & Restore* `.xml`.
The prompt-version selector lets you compare v1 and v4 live. Categories are editable in the table and
the charts follow the edit.

After one successful run on the sample data, a **Load sample results (offline)** button appears, so the
demo still works without network.

## Run the evaluation

```bash
python eval/run_eval.py --exp E1,E4,E2      # about 12 requests
python eval/run_eval.py --exp E1H           # about 6 requests
python eval/run_eval.py --exp E3            # about 12 requests

python eval/run_eval.py --runs 3            # everything, three runs each: needs a paid key
```

On the free tier, spread these over models or days. To use a different model for one run without
editing `.env`: `MODEL_NAME=gemini-3.5-flash-lite python eval/run_eval.py --exp E1H`

| Experiment | What it compares |
|---|---|
| E1 | Prompts v1 → v4 on the 60 labelled SMS in `data/test_sms.csv` (pre-filter off) |
| E1H | The same ablation on the 24 harder SMS in `data/test_sms_hard.csv` |
| E2 | Pre-filter on vs off: API calls saved, real transactions wrongly dropped |
| E3 | Batch size 10 / 30 / 60 |
| E4 | Categorization: rules only / LLM only / hybrid |

E1, E1H and E2 send 30 SMS per call by default (`--batch-size`). v4 uses the same prompt text as v3, so
its first calls come from the cache and it only costs requests when the repair loop fires.

Outputs go to `eval/results/`: `results.csv` (model, mean, std and per-run values for every metric),
`ablation_chart.png` and `failure_log.md` for E1, and `ablation_chart_hard.png` and `failure_log_hard.md`
for E1H. The failure logs list every wrong prediction plus three before/after candidates.

Responses are cached per model in `eval/results/.cache`. If the daily quota runs out, the script stops,
saves the configurations that finished, and continues from there when you re-run the same command.
Delete the cache folder to force fresh calls.

## Offline self-check

```bash
python test_pipeline.py
```

Runs the whole pipeline against a stub LLM that answers from the labels. It checks the filter, masking,
dedupe, validation, the repair loop, the rules, the aggregation and the metrics. No API key needed.

## Layout

| Path | Contents |
|---|---|
| `app.py` | Streamlit dashboard |
| `pipeline/llm.py` | The only file that calls the LLM; rewrite `call()` to switch provider |
| `pipeline/preprocess.py` | Input parsers, noise filter, dedupe, PII masking |
| `pipeline/extract.py` | Batched extraction, validation, repair loop (v4) |
| `pipeline/categorize.py` | Merchant rules, LLM fallback, cache |
| `pipeline/aggregate.py`, `insights.py` | Summary numbers; insights with a number-grounding check |
| `prompts/` | `extract_v1…v4`, `repair`, `categorize`, `insights` |
| `data/` | `sample_sms.txt` (demo), `test_sms.csv` (60 labelled), `test_sms_hard.csv` (24 harder cases), `merchant_rules.json` |
| `eval/` | `run_eval.py`, `metrics.py`, `results/` |
| `REPORT.md`, `DEMO_SCRIPT.md` | Project report with the measured results; 5-minute presentation script |

## Where this differs from the plan

- **Structured output is on for all four prompt versions**, as in the plan's `extract_batch` code. The
  ablation therefore measures the prompt text alone, and the valid-JSON rate will be close to 100% for every
  version. The repair loop in v4 earns its keep on semantic errors (ungrounded amounts, missing fields, bad dates).
- **Noise filter:** the plan's regex dropped 5 of the 40 real transactions in the test set (SBI's
  currency-less "debited by 249.00", BoB's "Dr./Cr.", SBI debit card "done at", HDFC "deposited").
  The verb list and amount pattern were extended, after which it drops none. The filter and the test set
  were written together, so read E2's zero as a best case.
- **Merchant accuracy** uses `rapidfuzz.token_set_ratio ≥ 80` instead of plain `ratio`, so "Starbucks" and
  "Starbucks Coffee" count as the same merchant.
- **Spend by category** is drawn as ranked bars instead of a pie: with up to 15 categories, bars are readable and a pie is not.
- **E4** feeds the categorizer the labelled merchant, type and mode, so extraction mistakes don't leak into it.
- **E3** compares batch sizes 10 / 30 / 60. The plan's batch size 1 costs 61 requests per run, three days of free-tier quota.
- **Runs and batch size:** the eval defaults to one run per configuration (`--runs 3` for the plan's three). The app and
  the eval send 30 SMS per call instead of 10, because E3 found no accuracy difference and each request counts against the quota.
- **Hard set (E1H):** not in the plan. The 60-SMS core set turned out too easy to separate v2, v3 and v4.
- **Payment mode** is scored as an extra field (null and `OTHER` count as the same answer), so overall field accuracy is the mean of seven fields, not six.
- **E5** (second model) is not implemented.
- `data/cache.json` (merchant → category) never stores entries classified as *Transfers to People*, so names of people stay off disk.

## Privacy

Account and card numbers, reference numbers, phone numbers and emails are masked before any API call.
The insights prompt sees only aggregated numbers. SMS text is held in the Streamlit session and is not
written to disk. The evaluation data is synthetic.

Not financial advice.
