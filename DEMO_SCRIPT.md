# Demo script (about 5 minutes)

## Before you present

- Run `streamlit run app.py`, click **Load sample data**, then **Analyze** once. That uses 4 API requests
  and creates the offline results file.
- During the talk, use **Load sample results (offline)**. It needs no network and no quota.
- Keep `eval/results/ablation_chart.png` and `ablation_chart_hard.png` open in another tab.
- If you want one live run, check the quota first: 20 requests per day per model.

## 1. Problem (30 s)

"Every UPI payment and card swipe sends an SMS, and every bank words it differently. They sit between
OTPs and offers, so nobody adds them up. Regex parsers break when a template changes. My first noise
filter, written from memory, dropped 5 of 40 real transactions. Can a prompt do better?"

## 2. Architecture (45 s)

Show the pipeline diagram from the README.

"Six steps. Python filters noise and masks account numbers before anything leaves the machine. The LLM
extracts fields as JSON. Python validates them and checks the amount really appears in the message. Rules
categorize known merchants and the LLM handles the rest. pandas does all the arithmetic. The LLM then
writes insights from the totals only. The model is used only where rules fail, and it never does maths."

## 3. Prompt evolution (90 s)

Open `prompts/extract_v1.txt`, then `extract_v2.txt`, then scroll to the examples in `extract_v3.txt`.

- "v1 is one line. It finds every transaction, but returns dates as written: `07Nov26`."
- "v2 adds a role, field definitions and ten rules. Dates are fixed. But for a failed payment with no date
  in the text, it invents one, even though rule 9 says never guess."
- "v3 adds six worked examples. One shows `date: null` for a failed payment. The invented dates stop."
- "v4 adds a repair loop: if validation fails, the error list goes back to the model."

## 4. Results (60 s)

Show `ablation_chart.png`, then `ablation_chart_hard.png`.

- "On 60 labelled SMS: 85.7% field accuracy for v1, 98.6% for v2, 99.6% for v3 and v4. Detection is perfect
  for all four."
- "That set turned out too easy, so I wrote 24 harder messages: fees next to the amount, foreign currency,
  missing dates. There the versions separate: 83.9%, 96.4%, 98.2%."
- "Honest caveat: the repair loop never fired, so v4 equals v3 in these runs."
- "Side results: the pre-filter sends 44 messages instead of 60 with no loss. Rules plus LLM categorization
  reaches 100%, against 85% for rules alone and 70% for the LLM alone."

## 5. Live demo (60 s)

1. Click **Load sample results (offline)**, or **Load sample data** then **Analyze** for a live run.
2. Point at the run stats: 35 SMS in, 3 filtered as noise, 1 duplicate removed.
3. Scroll the transactions table. Show the masked SMS column. Change one category and watch the chart update.
4. Show spend by category, weekly spend and top merchants.
5. Read one AI insight aloud. "Every rupee figure here is checked against the computed summary."

## 6. Takeaways (15 s)

"Most of the gain came from a schema and explicit rules. Examples fixed what rules could not enforce. And
plain code around the model did as much as the prompts."
