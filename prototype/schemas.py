from typing import Literal

from pydantic import BaseModel


ReceiptStatus = Literal["Reviewable", "Caution", "Not recommended as PR"]


class PublicReceipt(BaseModel):
    status: ReceiptStatus
    policy_fit: str
    human_ownership: str
    ai_role: str
    evidence_reviewed: str
    tests_checks_run: str
    reviewer_attention_requested: str
    known_risks_or_unknowns: str
    recommended_next_step: str
    receipt_binding: str


class ReceiptResult(BaseModel):
    public_receipt: PublicReceipt
