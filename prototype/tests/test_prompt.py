from pathlib import Path

from prototype.github_context import PullRequestContext
from prototype.prompt import build_receipt_prompt
from prototype.transcript import Transcript


class TestBuildReceiptPrompt:
    def test_includes_transcript_fields(self):
        loaded_transcript = Transcript(
            path=Path("transcripts/session.txt"),
            mode="text",
            content="user: please keep the CLI change narrow",
        )
        pr_context = PullRequestContext(
            number=3,
            title="Add CLI receipt output",
            body="This PR adds receipt output.",
            url="https://github.com/owner/repo/pull/3",
            head_sha="abc123",
        )

        prompt = build_receipt_prompt(loaded_transcript, pr_context)

        assert "Transcript path: transcripts/session.txt" in prompt
        assert "Transcript mode: text" in prompt
        assert "user: please keep the CLI change narrow" in prompt

    def test_includes_pr_context_fields(self):
        loaded_transcript = Transcript(
            path=Path("transcripts/session.txt"),
            mode="text",
            content="assistant: tests passed",
        )
        pr_context = PullRequestContext(
            number=42,
            title="Preserve reviewer intent",
            body="Adds the ownership receipt scaffold.",
            url="https://github.com/owner/repo/pull/42",
            head_sha="feedface",
        )

        prompt = build_receipt_prompt(loaded_transcript, pr_context)

        assert "PR number: 42" in prompt
        assert "PR title: Preserve reviewer intent" in prompt
        assert "PR body: Adds the ownership receipt scaffold." in prompt
        assert "PR URL: https://github.com/owner/repo/pull/42" in prompt
        assert "PR head SHA: feedface" in prompt

    def test_includes_no_evidence_rule(self):
        loaded_transcript = Transcript(
            path=Path("transcripts/session.txt"),
            mode="text",
            content="assistant: implemented the change",
        )
        pr_context = PullRequestContext(
            number=3,
            title="Add receipt context",
            body="",
            url="https://github.com/owner/repo/pull/3",
            head_sha="abc123",
        )

        prompt = build_receipt_prompt(loaded_transcript, pr_context)

        assert (
            "If the transcript does not show a kind of contributor ownership, do not credit that ownership "
            "merely because the PR description, issue response, or generated artifact looks coherent."
        ) in prompt

    def test_includes_missing_context_markers(self):
        loaded_transcript = Transcript(
            path=Path("transcripts/session.txt"),
            mode="text",
            content="user: ship it",
        )
        pr_context = PullRequestContext(
            number=3,
            title="Add receipt context",
            body="",
            url="https://github.com/owner/repo/pull/3",
            head_sha="abc123",
        )

        prompt = build_receipt_prompt(loaded_transcript, pr_context)

        assert "Issue context: no issue context provided" in prompt
        assert "Policy context: no policy found" in prompt

    def test_names_public_receipt_fields(self):
        loaded_transcript = Transcript(
            path=Path("transcripts/session.txt"),
            mode="text",
            content="user: please review the result against the issue",
        )
        pr_context = PullRequestContext(
            number=3,
            title="Add receipt context",
            body="",
            url="https://github.com/owner/repo/pull/3",
            head_sha="abc123",
        )

        prompt = build_receipt_prompt(loaded_transcript, pr_context)

        expected_fields = [
            "status",
            "policy_fit",
            "human_ownership",
            "ai_role",
            "evidence_reviewed",
            "tests_checks_run",
            "reviewer_attention_requested",
            "known_risks_or_unknowns",
            "recommended_next_step",
            "receipt_binding",
        ]
        for field in expected_fields:
            assert f"- {field}" in prompt

    def test_requests_current_receipt_result_schema(self):
        loaded_transcript = Transcript(
            path=Path("transcripts/session.txt"),
            mode="text",
            content="user: keep the receipt focused",
        )
        pr_context = PullRequestContext(
            number=3,
            title="Add receipt context",
            body="",
            url="https://github.com/owner/repo/pull/3",
            head_sha="abc123",
        )

        prompt = build_receipt_prompt(loaded_transcript, pr_context)

        assert "- public_receipt" in prompt
        assert "private_evaluation" not in prompt
