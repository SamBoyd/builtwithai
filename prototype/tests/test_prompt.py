from pathlib import Path

from prototype.github_context import IssueContext, PullRequestContext
from prototype.policy import PolicyContext
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

    def test_includes_issue_context_when_provided(self):
        loaded_transcript = Transcript(
            path=Path("transcripts/session.txt"),
            mode="text",
            content="user: please implement the issue exactly",
        )
        pr_context = PullRequestContext(
            number=3,
            title="Add receipt context",
            body="",
            url="https://github.com/owner/repo/pull/3",
            head_sha="abc123",
        )
        issue_context = IssueContext(
            number=1,
            title="Support issue context",
            body="The receipt should know the original request.",
        )

        prompt = build_receipt_prompt(loaded_transcript, pr_context, issue_context)

        assert "Issue context:\n" in prompt
        assert "Issue number: 1" in prompt
        assert "Issue title: Support issue context" in prompt
        assert "Issue body: The receipt should know the original request." in prompt
        assert "Issue context: no issue context provided" not in prompt

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
        assert "- private_evaluation" in prompt

    def test_requests_private_evaluation_rubric_answers(self):
        loaded_transcript = Transcript(
            path=Path("transcripts/session.txt"),
            mode="text",
            content="user: please explain the review risk",
        )
        pr_context = PullRequestContext(
            number=3,
            title="Add private evaluation",
            body="",
            url="https://github.com/owner/repo/pull/3",
            head_sha="abc123",
        )

        prompt = build_receipt_prompt(loaded_transcript, pr_context)

        expected_questions = [
            "Did the contributor understand the issue before implementation?",
            "Did they ask clarifying questions or challenge assumptions?",
            "Did they evaluate alternative solutions?",
            "Did they approve or modify the plan for reasons they could explain?",
            "Did they make tradeoff judgments?",
            "Did they notice missing tests, edge cases, or refactor opportunities?",
            "Did they steer the work rather than merely accept generated output?",
            "Did they review the final change in relation to the original issue?",
            "Did they show they could answer maintainer questions?",
        ]
        for question in expected_questions:
            assert question in prompt

        assert "ownership_rubric_answers" in prompt
        assert "question" in prompt
        assert "evidence_level" in prompt
        assert "evidence" in prompt

    def test_private_evaluation_instructions_include_evidence_levels_and_extra_questions(self):
        loaded_transcript = Transcript(
            path=Path("transcripts/session.txt"),
            mode="text",
            content="user: decide whether this needs reviewer caution",
        )
        pr_context = PullRequestContext(
            number=3,
            title="Add private evaluation",
            body="",
            url="https://github.com/owner/repo/pull/3",
            head_sha="abc123",
        )

        prompt = build_receipt_prompt(loaded_transcript, pr_context)

        assert "visible" in prompt
        assert "weak" in prompt
        assert "missing" in prompt
        assert "contradictory" in prompt

    def test_includes_policy_context_when_provided(self):
        loaded_transcript = Transcript(
            path=Path("transcripts/session.txt"),
            mode="text",
            content="user: I checked the repo policy",
        )
        pr_context = PullRequestContext(
            number=3,
            title="Add policy context",
            body="",
            url="https://github.com/owner/repo/pull/3",
            head_sha="abc123",
        )
        policy_context = PolicyContext(
            status="provided",
            path=Path("AI_POLICY.md"),
            content="AI-assisted contributions must disclose AI use.",
        )

        prompt = build_receipt_prompt(
            loaded_transcript,
            pr_context,
            policy_context=policy_context,
        )

        assert "Policy context:\n" in prompt
        assert "Policy status: provided" in prompt
        assert "Policy path: AI_POLICY.md" in prompt
        assert "AI-assisted contributions must disclose AI use." in prompt
        assert "Policy context: no policy found" not in prompt

    def test_missing_policy_context_keeps_missing_marker_and_instruction(self):
        loaded_transcript = Transcript(
            path=Path("transcripts/session.txt"),
            mode="text",
            content="user: ship it",
        )
        pr_context = PullRequestContext(
            number=3,
            title="Add policy context",
            body="",
            url="https://github.com/owner/repo/pull/3",
            head_sha="abc123",
        )
        policy_context = PolicyContext(status="none_found", path=None, content="")

        prompt = build_receipt_prompt(
            loaded_transcript,
            pr_context,
            policy_context=policy_context,
        )

        assert "Policy context: no policy found" in prompt
        assert "policy_fit must say that no clear repository AI policy was available" in prompt
