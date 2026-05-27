import pytest
from pydantic import ValidationError

from prototype.schemas import PublicReceipt, ReceiptResult


def make_receipt(**overrides):
    values = {
        "status": "Caution",
        "policy_fit": "",
        "human_ownership": "",
        "ai_role": "",
        "evidence_reviewed": "",
        "tests_checks_run": "",
        "reviewer_attention_requested": "",
        "known_risks_or_unknowns": "",
        "recommended_next_step": "",
        "receipt_binding": "",
    }
    values.update(overrides)
    return PublicReceipt(**values)


def test_public_receipt_accepts_required_fields():
    receipt = make_receipt(policy_fit="No policy found.")

    assert receipt.status == "Caution"
    assert receipt.policy_fit == "No policy found."


def test_public_receipt_rejects_invalid_status():
    with pytest.raises(ValidationError):
        make_receipt(status="Ready")


def test_public_receipt_requires_all_fields():
    values = make_receipt().model_dump()
    del values["receipt_binding"]

    with pytest.raises(ValidationError):
        PublicReceipt(**values)


def test_receipt_result_stores_public_receipt():
    receipt = make_receipt(status="Reviewable")
    result = ReceiptResult(public_receipt=receipt)

    assert result.public_receipt == receipt
