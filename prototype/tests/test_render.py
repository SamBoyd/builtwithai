from prototype.render import render_public_receipt
from prototype.schemas import PublicReceipt


def make_receipt():
    return PublicReceipt(
        status="Reviewable",
        policy_fit="Policy allows AI-assisted contributions with human ownership.",
        human_ownership="The transcript shows visible steering and final review.",
        ai_role="AI drafted code, tests, and PR copy under contributor direction.",
        evidence_reviewed="Transcript and PR metadata.",
        tests_checks_run="pytest prototype/tests -q.",
        reviewer_attention_requested="Review the implementation boundary.",
        known_risks_or_unknowns="No policy file was evaluated in this slice.",
        recommended_next_step="Review the PR.",
        receipt_binding="PR #3.",
    )


def test_render_public_receipt_matches_required_markdown():
    receipt = make_receipt()

    assert render_public_receipt(receipt) == (
        "BuiltWithAi PR Ownership Receipt\n"
        "\n"
        "Status: Reviewable\n"
        "\n"
        "Policy fit: Policy allows AI-assisted contributions with human ownership.\n"
        "\n"
        "Human ownership: The transcript shows visible steering and final review.\n"
        "\n"
        "AI role: AI drafted code, tests, and PR copy under contributor direction.\n"
        "\n"
        "Evidence reviewed: Transcript and PR metadata.\n"
        "\n"
        "Tests/checks run: pytest prototype/tests -q.\n"
        "\n"
        "Reviewer attention requested: Review the implementation boundary.\n"
        "\n"
        "Known risks or unknowns: No policy file was evaluated in this slice.\n"
        "\n"
        "Recommended next step: Review the PR.\n"
        "\n"
        "Receipt binding: PR #3.\n"
    )


def test_render_public_receipt_includes_each_label_once():
    markdown = render_public_receipt(make_receipt())

    labels = [
        "Status:",
        "Policy fit:",
        "Human ownership:",
        "AI role:",
        "Evidence reviewed:",
        "Tests/checks run:",
        "Reviewer attention requested:",
        "Known risks or unknowns:",
        "Recommended next step:",
        "Receipt binding:",
    ]
    for label in labels:
        assert markdown.count(label) == 1
