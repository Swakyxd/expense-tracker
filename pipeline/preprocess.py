"""Step 1: parse input, drop noise, dedupe, mask PII. No LLM."""
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

import pandas as pd

from .schema import Sms

DROP = re.compile(
    r"\b(otp|one[- ]time password|verification code|do not share|offer|cashback upto|"
    r"win |congratulations|pre-approved|loan approved|kyc|click here to)\b", re.I)
# Plan's verb list + "deposited", "Dr./Cr." and "done at": the first filter run on
# data/test_sms.csv dropped real HDFC NEFT, BoB UPI and SBI debit-card messages without them.
KEEP_VERB = re.compile(
    r"\b(debited|credited|spent|sent|received|withdrawn|paid|transferred|refund(ed)?|"
    r"reversed|declined|failed|deposited|dr|cr|done at)\b", re.I)
# Second alternative catches SBI's currency-less "debited by 249.00".
AMOUNT = re.compile(r"(?:\b(?:rs\.?|inr)|₹)\s?(\d[\d,]*(?:\.\d{1,2})?)|\b(?:by|of|for)\s(\d[\d,]*\.\d{2})\b", re.I)
REF = re.compile(r"(?<!\d)\d{12}(?!\d)")
NOT_SUCCESS = re.compile(r"revers|refund|fail|declin|unsuccess", re.I)


def _sms(i, body, ts=None) -> Sms:
    return Sms(i, " ".join(str(body).split()), ts)  # one line per SMS


def parse_text(text: str) -> list[Sms]:
    blocks = re.split(r"\n\s*\n", text.strip())
    if len(blocks) == 1:  # no blank lines: assume one SMS per line
        blocks = text.strip().splitlines()
    return [_sms(i, b) for i, b in enumerate((b for b in blocks if b.strip()), 1)]


def parse_csv(file) -> list[Sms]:
    df = pd.read_csv(file)
    col = next((c for c in ("body", "sms") if c in df.columns), None)
    if col is None:
        raise ValueError("CSV needs a 'body' column (optional: 'date').")
    dates = pd.to_datetime(df["date"], errors="coerce", dayfirst=True) if "date" in df.columns else [None] * len(df)
    return [_sms(i, body, None if pd.isna(ts) else ts.to_pydatetime())
            for i, (body, ts) in enumerate(zip(df[col], dates), 1) if isinstance(body, str) and body.strip()]


def parse_xml(file) -> list[Sms]:
    """Android 'SMS Backup & Restore' export: <sms body="..." date="epoch-ms" address="...">."""
    out = []
    for i, el in enumerate(ET.parse(file).getroot().iter("sms"), 1):
        ms = el.get("date", "")
        out.append(_sms(i, el.get("body", ""), datetime.fromtimestamp(int(ms) / 1000) if ms.isdigit() else None))
    return [s for s in out if s.text]


def is_candidate(text: str) -> bool:
    return bool(AMOUNT.search(text) and KEEP_VERB.search(text) and not DROP.search(text))


def mask(text: str) -> str:
    # ponytail: a VPA written like "name@bank.word" would be masked as an email; none seen in bank SMS so far
    text = re.sub(r"[\w.+-]+@[\w-]+(?:\.[a-z]{2,})+\b", "[EMAIL]", text)
    text = re.sub(r"(?<![A-Za-z\d])[Xx*]+(\d{3,4})\b", r"XX\1", text)             # X4521, *4417, XXXXXXXX3390
    text = REF.sub("[REF]", text)                                                 # UPI ref / RRN
    text = re.sub(r"(?<!\d)[6-9]\d{9}(?!\d)", "[PHONE]", text)
    text = re.sub(r"(?<!\d)(?!18[06]0)\d{5,14}(\d{4})(?!\d)", r"XX\1", text)      # other 9-18 digit runs, not helplines
    return text


def _dedupe_key(text: str):
    amount, ref = AMOUNT.search(text), REF.search(text)
    if amount and ref:
        value = float((amount.group(1) or amount.group(2)).replace(",", ""))
        # failure and reversal notices share the ref of the original payment but are different events
        event = NOT_SUCCESS.search(text)
        return value, ref.group(), event.group().lower() if event else None


def preprocess(messages: list[Sms], use_filter: bool = True):
    """Returns (kept, noise, n_duplicates). Text is masked in both lists."""
    kept, noise, seen, duplicates = [], [], {}, 0
    for m in messages:
        if use_filter and not is_candidate(m.text):
            noise.append(m._replace(text=mask(m.text)))
            continue
        key = _dedupe_key(m.text)  # on the unmasked text: masking removes the ref
        if key:
            if key in seen and (m.ts is None or seen[key] is None or abs(m.ts - seen[key]) <= timedelta(minutes=5)):
                duplicates += 1
                continue
            seen[key] = m.ts
        kept.append(m._replace(text=mask(m.text)))
    return kept, noise, duplicates
