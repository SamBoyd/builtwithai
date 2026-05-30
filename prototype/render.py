from prototype.schemas import PrivateEvaluation, PublicReceipt


def render_public_receipt(receipt: PublicReceipt) -> str:
    return (
        "BuiltWithAi PR Ownership Receipt\n"
        "\n"
        f"Status: {receipt.status}\n"
        "\n"
        f"Policy fit: {receipt.policy_fit}\n"
        "\n"
        f"Human ownership: {receipt.human_ownership}\n"
        "\n"
        f"AI role: {receipt.ai_role}\n"
        "\n"
        f"Evidence reviewed: {receipt.evidence_reviewed}\n"
        "\n"
        f"Tests/checks run: {receipt.tests_checks_run}\n"
        "\n"
        f"Reviewer attention requested: {receipt.reviewer_attention_requested}\n"
        "\n"
        f"Known risks or unknowns: {receipt.known_risks_or_unknowns}\n"
        "\n"
        f"Recommended next step: {receipt.recommended_next_step}\n"
        "\n"
        f"Receipt binding: {receipt.receipt_binding}\n"
    )


def render_private_evaluation(private_evaluation: PrivateEvaluation) -> str:
    return f"{private_evaluation.model_dump_json(indent=2)}\n"
