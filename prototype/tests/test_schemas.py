import pytest
from pydantic import ValidationError

from prototype.schemas import (
    OwnershipRubricAnswer,
    PrivateEvaluation,
    PublicReceipt,
    ReceiptResult,
)


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
    private_evaluation = PrivateEvaluation(
        ownership_rubric_answers=[
            OwnershipRubricAnswer(
                question="Did the contributor understand the issue before implementation?",
                evidence_level="visible",
                evidence="The transcript shows the contributor restating the issue.",
            )
        ]
    )
    result = ReceiptResult(
        public_receipt=receipt,
        private_evaluation=private_evaluation,
    )

    assert result.public_receipt == receipt
    assert result.private_evaluation == private_evaluation


class TestPrivateEvaluation:
    def test_private_evaluation_accepts_rubric_answers(self):
        answer = OwnershipRubricAnswer(
            question="Did they steer the work rather than merely accept generated output?",
            evidence_level="weak",
            evidence="The transcript shows acceptance but limited steering.",
        )
        evaluation = PrivateEvaluation(ownership_rubric_answers=[answer])

        assert evaluation.ownership_rubric_answers == [answer]

    def test_ownership_rubric_answer_rejects_invalid_evidence_level(self):
        with pytest.raises(ValidationError):
            OwnershipRubricAnswer(
                question="Did they evaluate alternative solutions?",
                evidence_level="strong",
                evidence="The transcript discusses two implementation paths.",
            )

    def test_ownership_rubric_answer_requires_question_level_and_evidence(self):
        with pytest.raises(ValidationError):
            OwnershipRubricAnswer(
                question="Did they ask clarifying questions or challenge assumptions?",
                evidence_level="missing",
            )

    def test_receipt_result_requires_private_evaluation(self):
        with pytest.raises(ValidationError):
            ReceiptResult(public_receipt=make_receipt())
