from datetime import datetime
from typing import Literal, NamedTuple, Optional

from pydantic import BaseModel, field_validator

CATEGORIES = [
    "Food & Dining", "Groceries", "Travel & Transport", "Shopping", "Bills & Recharges",
    "Entertainment & Subscriptions", "Health", "Education", "Rent & Housing",
    "Transfers to People", "Investments", "Cash Withdrawal", "Income", "Refund", "Other",
]


class Sms(NamedTuple):
    id: int
    text: str
    ts: Optional[datetime] = None  # timestamp from the backup file, if any


class Transaction(BaseModel):
    id: int
    is_transaction: bool
    type: Optional[Literal["debit", "credit"]] = None
    amount: Optional[float] = None
    merchant: Optional[str] = None
    date: Optional[str] = None  # ISO YYYY-MM-DD
    mode: Optional[Literal["UPI", "CARD", "NEFT_IMPS", "ATM", "AUTOPAY", "OTHER"]] = None
    status: Optional[Literal["success", "failed", "reversed"]] = None
    account_last4: Optional[str] = None

    # A validator, not Field(gt=0): gt puts "exclusiveMinimum" in the JSON schema, which Gemini's response_schema rejects.
    @field_validator("amount")
    @classmethod
    def _positive(cls, v):
        if v is not None and v <= 0:
            raise ValueError("must be greater than 0")
        return v
