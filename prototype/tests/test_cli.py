import json
from types import SimpleNamespace
from unittest.mock import patch

from click.testing import CliRunner

from prototype.cli import GitHubContextError, cli
from prototype.llm_client import LLMClientError
from prototype.policy import PolicyContext
from prototype.schemas import (
    OwnershipRubricAnswer,
    PrivateEvaluation,
    PublicReceipt,
    ReceiptResult,
    ReceiptStatus,
)


def pr_reference(number=3, repo=None):
    return SimpleNamespace(number=number, repo=repo)


def issue_reference(number=1, repo=None):
    return SimpleNamespace(number=number, repo=repo)


def pr_context(
    number=3, title="Add receipt context", body="", url=None, head_sha="abc123"
):
    return SimpleNamespace(
        number=number,
        title=title,
        body=body,
        url=url or f"https://github.com/owner/repo/pull/{number}",
        head_sha=head_sha,
    )


def issue_context(number=1, title="Support issue context", body="Issue body"):
    return SimpleNamespace(number=number, title=title, body=body)


def policy_context(status="none_found", path=None, content=""):
    return PolicyContext(status=status, path=path, content=content)


def receipt_result(
    status: ReceiptStatus = "Reviewable", receipt_binding="LLM receipt binding."
):
    return ReceiptResult(
        public_receipt=PublicReceipt(
            status=status,
            policy_fit="No policy found.",
            human_ownership="The transcript shows visible human steering.",
            ai_role="AI drafted code under contributor direction.",
            evidence_reviewed="Transcript and GitHub PR metadata.",
            tests_checks_run="pytest prototype/tests -q.",
            reviewer_attention_requested="Review the implementation boundary.",
            known_risks_or_unknowns="No issue or policy context was provided.",
            recommended_next_step="Review the PR.",
            receipt_binding=receipt_binding,
        ),
        private_evaluation=PrivateEvaluation(
            ownership_rubric_answers=[
                OwnershipRubricAnswer(
                    question="Did they steer the work rather than merely accept generated output?",
                    evidence_level="visible",
                    evidence="The transcript shows the contributor narrowing the requested change.",
                )
            ]
        ),
    )


class TestCliHelp:
    def test_shows_required_cli_surface(self):
        result = CliRunner().invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "TRANSCRIPT_PATH" in result.output
        assert "--pr" in result.output
        assert "--issue" in result.output
        assert "--repo" in result.output
        assert "--policy" in result.output
        assert "--show-private-eval" in result.output
        assert "--receipt-output" in result.output
        assert "--private-eval-output" in result.output
        assert "--overwrite" in result.output
        assert "Allow overwriting existing output files." in result.output


class TestReceiptGeneration:
    @patch("prototype.cli.get_repository_root")
    @patch("prototype.cli.load_policy_context")
    @patch("prototype.cli.get_origin_repository", return_value="owner/repo")
    @patch("prototype.cli.resolve_repository", return_value="owner/repo")
    @patch("prototype.cli.get_pull_request_context")
    @patch("prototype.cli.generate_receipt")
    @patch("prototype.cli.build_receipt_prompt", return_value="secret prompt")
    @patch("prototype.cli.parse_pr_reference", return_value=pr_reference(number=3))
    @patch("prototype.transcript.load_transcript")
    def test_numeric_pr_succeeds_with_transcript_file(
        self,
        load_transcript,
        parse_pr_reference,
        build_receipt_prompt,
        generate_receipt,
        get_pull_request_context,
        resolve_repository,
        get_origin_repository,
        load_policy_context,
        get_repository_root,
        tmp_path,
    ):
        loaded_transcript = SimpleNamespace(
            path=tmp_path / "transcript.txt", mode="text", content="user secret"
        )
        pr = pr_context(body="Do not print me")
        policy = policy_context()
        load_transcript.return_value = loaded_transcript
        get_repository_root.return_value = tmp_path
        load_policy_context.return_value = policy
        get_pull_request_context.return_value = pr
        generate_receipt.return_value = receipt_result()
        transcript_path = tmp_path / "transcript.txt"
        transcript_path.write_text("user: please make the change\n", encoding="utf-8")

        result = CliRunner().invoke(cli, [str(transcript_path), "--pr", "3"])

        assert result.exit_code == 0
        parse_pr_reference.assert_called_once_with("3")
        load_transcript.assert_called_once_with(transcript_path)
        resolve_repository.assert_called_once_with(None, None, get_origin_repository)
        get_pull_request_context.assert_called_once_with("owner/repo", 3)
        get_repository_root.assert_called_once_with()
        load_policy_context.assert_called_once_with(None, tmp_path)
        build_receipt_prompt.assert_called_once_with(
            loaded_transcript,
            pr,
            issue_context=None,
            policy_context=policy,
        )
        generate_receipt.assert_called_once_with("secret prompt")
        assert "BuiltWithAi PR Ownership Receipt" in result.output
        assert "Status: Reviewable" in result.output
        assert "The transcript shows visible human steering." in result.output
        assert "Transcript and GitHub PR metadata." in result.output
        assert "LLM receipt binding." in result.output
        assert "Do not print me" not in result.output
        assert "user secret" not in result.output
        assert "secret prompt" not in result.output
        assert "Transcript:" not in result.output
        assert "Private heuristic evaluation" not in result.output
        assert "ownership_rubric_answers" not in result.output

    @patch("prototype.cli.get_repository_root")
    @patch("prototype.cli.load_policy_context")
    @patch("prototype.transcript.load_transcript")
    @patch("prototype.cli.get_origin_repository", return_value="owner/repo")
    @patch("prototype.cli.resolve_repository", return_value="owner/repo")
    @patch("prototype.cli.get_pull_request_context")
    @patch("prototype.cli.generate_receipt")
    @patch("prototype.cli.build_receipt_prompt", return_value="receipt prompt")
    @patch("prototype.cli.parse_pr_reference", return_value=pr_reference(number=3))
    def test_loads_transcript_path(
        self,
        parse_pr_reference,
        build_receipt_prompt,
        generate_receipt,
        get_pull_request_context,
        resolve_repository,
        get_origin_repository,
        load_transcript,
        load_policy_context,
        get_repository_root,
        tmp_path,
    ):
        transcript_path = tmp_path / "transcript.txt"
        transcript_path.write_text("user: please make the change\n", encoding="utf-8")
        loaded_transcript = SimpleNamespace(
            path=transcript_path, mode="text", content="content"
        )
        pr = pr_context()
        policy = policy_context()
        load_transcript.return_value = loaded_transcript
        get_repository_root.return_value = tmp_path
        load_policy_context.return_value = policy
        get_pull_request_context.return_value = pr
        generate_receipt.return_value = receipt_result()

        result = CliRunner().invoke(cli, [str(transcript_path), "--pr", "3"])

        assert result.exit_code == 0
        load_transcript.assert_called_once_with(transcript_path)
        build_receipt_prompt.assert_called_once_with(
            loaded_transcript,
            pr,
            issue_context=None,
            policy_context=policy,
        )
        generate_receipt.assert_called_once_with("receipt prompt")

    @patch("prototype.cli.get_repository_root")
    @patch("prototype.cli.load_policy_context")
    @patch("prototype.cli.get_origin_repository", return_value="owner/repo")
    @patch("prototype.cli.resolve_repository", return_value="owner/repo")
    @patch("prototype.cli.get_issue_context")
    @patch("prototype.cli.get_pull_request_context")
    @patch("prototype.cli.generate_receipt")
    @patch("prototype.cli.build_receipt_prompt", return_value="receipt prompt")
    @patch("prototype.cli.parse_issue_reference", return_value=issue_reference(number=1))
    @patch("prototype.cli.parse_pr_reference", return_value=pr_reference(number=3))
    @patch("prototype.transcript.load_transcript")
    def test_fetches_explicit_issue_context(
        self,
        load_transcript,
        parse_pr_reference,
        parse_issue_reference,
        build_receipt_prompt,
        generate_receipt,
        get_pull_request_context,
        get_issue_context,
        resolve_repository,
        get_origin_repository,
        load_policy_context,
        get_repository_root,
        tmp_path,
    ):
        loaded_transcript = SimpleNamespace(
            path=tmp_path / "transcript.txt", mode="text", content="content"
        )
        pr = pr_context()
        issue = issue_context(number=1, title="Original request")
        policy = policy_context()
        load_transcript.return_value = loaded_transcript
        get_repository_root.return_value = tmp_path
        load_policy_context.return_value = policy
        get_pull_request_context.return_value = pr
        get_issue_context.return_value = issue
        generate_receipt.return_value = receipt_result()
        transcript_path = tmp_path / "transcript.txt"
        transcript_path.write_text("content\n", encoding="utf-8")

        result = CliRunner().invoke(cli, [str(transcript_path), "--pr", "3", "--issue", "1"])

        assert result.exit_code == 0
        parse_pr_reference.assert_called_once_with("3")
        parse_issue_reference.assert_called_once_with("1")
        resolve_repository.assert_called_once_with(None, None, get_origin_repository)
        get_pull_request_context.assert_called_once_with("owner/repo", 3)
        get_issue_context.assert_called_once_with("owner/repo", 1)
        build_receipt_prompt.assert_called_once_with(
            loaded_transcript,
            pr,
            issue_context=issue,
            policy_context=policy,
        )
        generate_receipt.assert_called_once_with("receipt prompt")

    @patch("prototype.cli.resolve_repository", return_value="owner/repo")
    @patch("prototype.cli.get_pull_request_context")
    @patch("prototype.cli.generate_receipt")
    @patch("prototype.cli.build_receipt_prompt", return_value="receipt prompt")
    @patch(
        "prototype.cli.parse_pr_reference",
        return_value=pr_reference(number=17, repo="owner/repo"),
    )
    @patch("prototype.transcript.load_transcript")
    def test_github_pr_url_succeeds_and_extracts_number(
        self,
        load_transcript,
        parse_pr_reference,
        build_receipt_prompt,
        generate_receipt,
        get_pull_request_context,
        resolve_repository,
        tmp_path,
    ):
        get_pull_request_context.return_value = pr_context(
            number=17, title="Add URL parsing", head_sha="def456"
        )
        generate_receipt.return_value = receipt_result(status="Caution")
        transcript_path = tmp_path / "transcript.txt"
        transcript_path.write_text("assistant: done\n", encoding="utf-8")

        result = CliRunner().invoke(
            cli,
            [str(transcript_path), "--pr", "https://github.com/owner/repo/pull/17"],
        )

        assert result.exit_code == 0
        parse_pr_reference.assert_called_once_with("https://github.com/owner/repo/pull/17")
        resolve_repository.assert_called_once()
        get_pull_request_context.assert_called_once_with("owner/repo", 17)
        build_receipt_prompt.assert_called_once()
        generate_receipt.assert_called_once_with("receipt prompt")
        assert "BuiltWithAi PR Ownership Receipt" in result.output
        assert "Status: Caution" in result.output

    @patch("prototype.cli.validate_repo", return_value="owner/repo")
    @patch("prototype.cli.resolve_repository", return_value="owner/repo")
    @patch("prototype.cli.get_pull_request_context")
    @patch("prototype.cli.generate_receipt")
    @patch("prototype.cli.build_receipt_prompt", return_value="receipt prompt")
    @patch("prototype.cli.parse_pr_reference", return_value=pr_reference(number=3))
    @patch("prototype.transcript.load_transcript")
    def test_uses_repo_option_for_numeric_pr(
        self,
        load_transcript,
        parse_pr_reference,
        build_receipt_prompt,
        generate_receipt,
        get_pull_request_context,
        resolve_repository,
        validate_repo,
        tmp_path,
    ):
        get_pull_request_context.return_value = pr_context()
        generate_receipt.return_value = receipt_result()
        transcript_path = tmp_path / "transcript.txt"
        transcript_path.write_text("content\n", encoding="utf-8")

        result = CliRunner().invoke(
            cli, [str(transcript_path), "--pr", "3", "--repo", "owner/repo"]
        )

        assert result.exit_code == 0
        validate_repo.assert_called_once_with("owner/repo")
        resolve_repository.assert_called_once()
        get_pull_request_context.assert_called_once_with("owner/repo", 3)
        build_receipt_prompt.assert_called_once()
        generate_receipt.assert_called_once_with("receipt prompt")

    @patch("prototype.cli.resolve_repository", return_value="owner/repo")
    @patch("prototype.cli.get_pull_request_context")
    @patch("prototype.cli.generate_receipt")
    @patch("prototype.cli.build_receipt_prompt", return_value="receipt prompt")
    @patch("prototype.cli.parse_pr_reference", return_value=pr_reference(number=42))
    @patch("prototype.transcript.load_transcript")
    def test_renders_llm_receipt_binding(
        self,
        load_transcript,
        parse_pr_reference,
        build_receipt_prompt,
        generate_receipt,
        get_pull_request_context,
        resolve_repository,
        tmp_path,
    ):
        get_pull_request_context.return_value = pr_context(
            number=42,
            title="Preserve reviewer intent",
            url="https://github.com/owner/repo/pull/42",
            head_sha="feedface",
        )
        generate_receipt.return_value = receipt_result(receipt_binding="LLM-bound PR #42.")
        transcript_path = tmp_path / "transcript.txt"
        transcript_path.write_text("content\n", encoding="utf-8")

        result = CliRunner().invoke(cli, [str(transcript_path), "--pr", "42"])

        assert result.exit_code == 0
        build_receipt_prompt.assert_called_once()
        generate_receipt.assert_called_once_with("receipt prompt")
        assert "Receipt binding: LLM-bound PR #42." in result.output


class TestPrivateEvaluationOutput:
    @patch("prototype.cli.get_repository_root")
    @patch("prototype.cli.load_policy_context")
    @patch("prototype.cli.get_origin_repository", return_value="owner/repo")
    @patch("prototype.cli.resolve_repository", return_value="owner/repo")
    @patch("prototype.cli.get_pull_request_context")
    @patch("prototype.cli.generate_receipt")
    @patch("prototype.cli.build_receipt_prompt", return_value="secret prompt")
    @patch("prototype.cli.parse_pr_reference", return_value=pr_reference(number=3))
    @patch("prototype.transcript.load_transcript")
    def test_show_private_eval_prints_public_receipt_then_private_json(
        self,
        load_transcript,
        parse_pr_reference,
        build_receipt_prompt,
        generate_receipt,
        get_pull_request_context,
        resolve_repository,
        get_origin_repository,
        load_policy_context,
        get_repository_root,
        tmp_path,
    ):
        transcript_path = tmp_path / "transcript.txt"
        transcript_path.write_text("content\n", encoding="utf-8")
        load_transcript.return_value = SimpleNamespace(
            path=transcript_path, mode="text", content="content"
        )
        get_repository_root.return_value = tmp_path
        load_policy_context.return_value = policy_context()
        get_pull_request_context.return_value = pr_context()
        generate_receipt.return_value = receipt_result()

        result = CliRunner().invoke(
            cli,
            [str(transcript_path), "--pr", "3", "--show-private-eval"],
        )

        assert result.exit_code == 0
        assert "BuiltWithAi PR Ownership Receipt" in result.output
        assert "Private heuristic evaluation" in result.output
        assert "ownership_rubric_answers" in result.output
        assert result.output.index("BuiltWithAi PR Ownership Receipt") < result.output.index(
            "Private heuristic evaluation"
        )

    @patch("prototype.cli.get_repository_root")
    @patch("prototype.cli.load_policy_context")
    @patch("prototype.cli.get_origin_repository", return_value="owner/repo")
    @patch("prototype.cli.resolve_repository", return_value="owner/repo")
    @patch("prototype.cli.get_pull_request_context")
    @patch("prototype.cli.generate_receipt")
    @patch("prototype.cli.build_receipt_prompt", return_value="secret prompt")
    @patch("prototype.cli.parse_pr_reference", return_value=pr_reference(number=3))
    @patch("prototype.transcript.load_transcript")
    def test_private_eval_output_writes_json_without_printing_private_eval(
        self,
        load_transcript,
        parse_pr_reference,
        build_receipt_prompt,
        generate_receipt,
        get_pull_request_context,
        resolve_repository,
        get_origin_repository,
        load_policy_context,
        get_repository_root,
        tmp_path,
    ):
        transcript_path = tmp_path / "transcript.txt"
        transcript_path.write_text("content\n", encoding="utf-8")
        private_eval_output = tmp_path / "private-eval.json"
        load_transcript.return_value = SimpleNamespace(
            path=transcript_path, mode="text", content="content"
        )
        get_repository_root.return_value = tmp_path
        load_policy_context.return_value = policy_context()
        get_pull_request_context.return_value = pr_context()
        generate_receipt.return_value = receipt_result()

        result = CliRunner().invoke(
            cli,
            [
                str(transcript_path),
                "--pr",
                "3",
                "--private-eval-output",
                str(private_eval_output),
            ],
        )

        assert result.exit_code == 0
        assert "BuiltWithAi PR Ownership Receipt" in result.output
        assert "Private heuristic evaluation" not in result.output
        assert "ownership_rubric_answers" not in result.output
        written = json.loads(private_eval_output.read_text(encoding="utf-8"))
        assert written["ownership_rubric_answers"][0]["evidence_level"] == "visible"

    @patch("prototype.cli.generate_receipt")
    @patch("prototype.cli.parse_pr_reference", return_value=pr_reference(number=3))
    @patch("prototype.transcript.load_transcript")
    def test_private_eval_output_existing_file_fails_without_overwrite(
        self,
        load_transcript,
        parse_pr_reference,
        generate_receipt,
        tmp_path,
    ):
        transcript_path = tmp_path / "transcript.txt"
        transcript_path.write_text("content\n", encoding="utf-8")
        private_eval_output = tmp_path / "private-eval.json"
        private_eval_output.write_text("existing\n", encoding="utf-8")

        result = CliRunner().invoke(
            cli,
            [
                str(transcript_path),
                "--pr",
                "3",
                "--private-eval-output",
                str(private_eval_output),
            ],
        )

        assert result.exit_code != 0
        assert "already exists" in result.output
        assert private_eval_output.read_text(encoding="utf-8") == "existing\n"
        generate_receipt.assert_not_called()

    @patch("prototype.cli.get_repository_root")
    @patch("prototype.cli.load_policy_context")
    @patch("prototype.cli.get_origin_repository", return_value="owner/repo")
    @patch("prototype.cli.resolve_repository", return_value="owner/repo")
    @patch("prototype.cli.get_pull_request_context")
    @patch("prototype.cli.generate_receipt")
    @patch("prototype.cli.build_receipt_prompt", return_value="secret prompt")
    @patch("prototype.cli.parse_pr_reference", return_value=pr_reference(number=3))
    @patch("prototype.transcript.load_transcript")
    def test_private_eval_output_overwrite_replaces_existing_file(
        self,
        load_transcript,
        parse_pr_reference,
        build_receipt_prompt,
        generate_receipt,
        get_pull_request_context,
        resolve_repository,
        get_origin_repository,
        load_policy_context,
        get_repository_root,
        tmp_path,
    ):
        transcript_path = tmp_path / "transcript.txt"
        transcript_path.write_text("content\n", encoding="utf-8")
        private_eval_output = tmp_path / "private-eval.json"
        private_eval_output.write_text("existing\n", encoding="utf-8")
        load_transcript.return_value = SimpleNamespace(
            path=transcript_path, mode="text", content="content"
        )
        get_repository_root.return_value = tmp_path
        load_policy_context.return_value = policy_context()
        get_pull_request_context.return_value = pr_context()
        generate_receipt.return_value = receipt_result()

        result = CliRunner().invoke(
            cli,
            [
                str(transcript_path),
                "--pr",
                "3",
                "--private-eval-output",
                str(private_eval_output),
                "--overwrite",
            ],
        )

        assert result.exit_code == 0
        written = json.loads(private_eval_output.read_text(encoding="utf-8"))
        assert written["ownership_rubric_answers"][0]["question"] == (
            "Did they steer the work rather than merely accept generated output?"
        )


class TestReceiptOutput:
    @patch("prototype.cli.get_repository_root")
    @patch("prototype.cli.load_policy_context")
    @patch("prototype.cli.get_origin_repository", return_value="owner/repo")
    @patch("prototype.cli.resolve_repository", return_value="owner/repo")
    @patch("prototype.cli.get_pull_request_context")
    @patch("prototype.cli.generate_receipt")
    @patch("prototype.cli.build_receipt_prompt", return_value="secret prompt")
    @patch("prototype.cli.parse_pr_reference", return_value=pr_reference(number=3))
    @patch("prototype.transcript.load_transcript")
    def test_receipt_output_writes_public_receipt_without_printing_it(
        self,
        load_transcript,
        parse_pr_reference,
        build_receipt_prompt,
        generate_receipt,
        get_pull_request_context,
        resolve_repository,
        get_origin_repository,
        load_policy_context,
        get_repository_root,
        tmp_path,
    ):
        transcript_path = tmp_path / "transcript.txt"
        transcript_path.write_text("content\n", encoding="utf-8")
        receipt_output = tmp_path / "receipt.md"
        load_transcript.return_value = SimpleNamespace(
            path=transcript_path, mode="text", content="content"
        )
        get_repository_root.return_value = tmp_path
        load_policy_context.return_value = policy_context()
        get_pull_request_context.return_value = pr_context()
        generate_receipt.return_value = receipt_result()

        result = CliRunner().invoke(
            cli,
            [
                str(transcript_path),
                "--pr",
                "3",
                "--receipt-output",
                str(receipt_output),
            ],
        )

        assert result.exit_code == 0
        assert result.output == ""
        written = receipt_output.read_text(encoding="utf-8")
        assert "BuiltWithAi PR Ownership Receipt" in written
        assert "Status: Reviewable" in written
        assert "The transcript shows visible human steering." in written
        assert "LLM receipt binding." in written
        assert "ownership_rubric_answers" not in written

    @patch("prototype.cli.generate_receipt")
    @patch("prototype.cli.parse_pr_reference", return_value=pr_reference(number=3))
    @patch("prototype.transcript.load_transcript")
    def test_receipt_output_existing_file_fails_without_overwrite(
        self,
        load_transcript,
        parse_pr_reference,
        generate_receipt,
        tmp_path,
    ):
        transcript_path = tmp_path / "transcript.txt"
        transcript_path.write_text("content\n", encoding="utf-8")
        receipt_output = tmp_path / "receipt.md"
        receipt_output.write_text("existing\n", encoding="utf-8")

        result = CliRunner().invoke(
            cli,
            [
                str(transcript_path),
                "--pr",
                "3",
                "--receipt-output",
                str(receipt_output),
            ],
        )

        assert result.exit_code != 0
        assert "already exists" in result.output
        assert receipt_output.read_text(encoding="utf-8") == "existing\n"
        generate_receipt.assert_not_called()

    @patch("prototype.cli.get_repository_root")
    @patch("prototype.cli.load_policy_context")
    @patch("prototype.cli.get_origin_repository", return_value="owner/repo")
    @patch("prototype.cli.resolve_repository", return_value="owner/repo")
    @patch("prototype.cli.get_pull_request_context")
    @patch("prototype.cli.generate_receipt")
    @patch("prototype.cli.build_receipt_prompt", return_value="secret prompt")
    @patch("prototype.cli.parse_pr_reference", return_value=pr_reference(number=3))
    @patch("prototype.transcript.load_transcript")
    def test_receipt_output_overwrite_replaces_existing_file(
        self,
        load_transcript,
        parse_pr_reference,
        build_receipt_prompt,
        generate_receipt,
        get_pull_request_context,
        resolve_repository,
        get_origin_repository,
        load_policy_context,
        get_repository_root,
        tmp_path,
    ):
        transcript_path = tmp_path / "transcript.txt"
        transcript_path.write_text("content\n", encoding="utf-8")
        receipt_output = tmp_path / "receipt.md"
        receipt_output.write_text("existing\n", encoding="utf-8")
        load_transcript.return_value = SimpleNamespace(
            path=transcript_path, mode="text", content="content"
        )
        get_repository_root.return_value = tmp_path
        load_policy_context.return_value = policy_context()
        get_pull_request_context.return_value = pr_context()
        generate_receipt.return_value = receipt_result(
            receipt_binding="Replacement binding."
        )

        result = CliRunner().invoke(
            cli,
            [
                str(transcript_path),
                "--pr",
                "3",
                "--receipt-output",
                str(receipt_output),
                "--overwrite",
            ],
        )

        assert result.exit_code == 0
        assert result.output == ""
        written = receipt_output.read_text(encoding="utf-8")
        assert "existing" not in written
        assert "Receipt binding: Replacement binding." in written

    @patch("prototype.cli.get_repository_root")
    @patch("prototype.cli.load_policy_context")
    @patch("prototype.cli.get_origin_repository", return_value="owner/repo")
    @patch("prototype.cli.resolve_repository", return_value="owner/repo")
    @patch("prototype.cli.get_pull_request_context")
    @patch("prototype.cli.generate_receipt")
    @patch("prototype.cli.build_receipt_prompt", return_value="secret prompt")
    @patch("prototype.cli.parse_pr_reference", return_value=pr_reference(number=3))
    @patch("prototype.transcript.load_transcript")
    def test_receipt_and_private_eval_outputs_write_both_files_without_stdout(
        self,
        load_transcript,
        parse_pr_reference,
        build_receipt_prompt,
        generate_receipt,
        get_pull_request_context,
        resolve_repository,
        get_origin_repository,
        load_policy_context,
        get_repository_root,
        tmp_path,
    ):
        transcript_path = tmp_path / "transcript.txt"
        transcript_path.write_text("content\n", encoding="utf-8")
        receipt_output = tmp_path / "receipt.md"
        private_eval_output = tmp_path / "private-eval.json"
        load_transcript.return_value = SimpleNamespace(
            path=transcript_path, mode="text", content="content"
        )
        get_repository_root.return_value = tmp_path
        load_policy_context.return_value = policy_context()
        get_pull_request_context.return_value = pr_context()
        generate_receipt.return_value = receipt_result()

        result = CliRunner().invoke(
            cli,
            [
                str(transcript_path),
                "--pr",
                "3",
                "--receipt-output",
                str(receipt_output),
                "--private-eval-output",
                str(private_eval_output),
            ],
        )

        assert result.exit_code == 0
        assert result.output == ""
        assert "BuiltWithAi PR Ownership Receipt" in receipt_output.read_text(
            encoding="utf-8"
        )
        written_private_eval = json.loads(private_eval_output.read_text(encoding="utf-8"))
        assert (
            written_private_eval["ownership_rubric_answers"][0]["evidence_level"]
            == "visible"
        )


class TestPolicyOption:
    @patch("prototype.cli.get_repository_root")
    @patch("prototype.cli.load_policy_context")
    @patch("prototype.cli.get_origin_repository", return_value="owner/repo")
    @patch("prototype.cli.resolve_repository", return_value="owner/repo")
    @patch("prototype.cli.get_pull_request_context")
    @patch("prototype.cli.generate_receipt")
    @patch("prototype.cli.build_receipt_prompt", return_value="receipt prompt")
    @patch("prototype.cli.parse_pr_reference", return_value=pr_reference(number=3))
    @patch("prototype.transcript.load_transcript")
    def test_loads_explicit_policy_path(
        self,
        load_transcript,
        parse_pr_reference,
        build_receipt_prompt,
        generate_receipt,
        get_pull_request_context,
        resolve_repository,
        get_origin_repository,
        load_policy_context,
        get_repository_root,
        tmp_path,
    ):
        loaded_transcript = SimpleNamespace(
            path=tmp_path / "transcript.txt", mode="text", content="content"
        )
        transcript_path = tmp_path / "transcript.txt"
        transcript_path.write_text("content\n", encoding="utf-8")
        policy_path = tmp_path / "AI_POLICY.md"
        policy_path.write_text("Policy text.\n", encoding="utf-8")
        policy = policy_context(status="provided", path=policy_path, content="Policy text.\n")
        load_transcript.return_value = loaded_transcript
        get_repository_root.return_value = tmp_path
        load_policy_context.return_value = policy
        get_pull_request_context.return_value = pr_context()
        generate_receipt.return_value = receipt_result()

        result = CliRunner().invoke(
            cli,
            [str(transcript_path), "--pr", "3", "--policy", str(policy_path)],
        )

        assert result.exit_code == 0
        get_repository_root.assert_called_once_with()
        load_policy_context.assert_called_once_with(policy_path, tmp_path)
        build_receipt_prompt.assert_called_once_with(
            loaded_transcript,
            get_pull_request_context.return_value,
            issue_context=None,
            policy_context=policy,
        )
        generate_receipt.assert_called_once_with("receipt prompt")

    @patch("prototype.cli.get_repository_root")
    @patch("prototype.cli.load_policy_context")
    @patch("prototype.cli.get_origin_repository", return_value="owner/repo")
    @patch("prototype.cli.resolve_repository", return_value="owner/repo")
    @patch("prototype.cli.get_pull_request_context")
    @patch("prototype.cli.generate_receipt")
    @patch("prototype.cli.build_receipt_prompt", return_value="receipt prompt")
    @patch("prototype.cli.parse_pr_reference", return_value=pr_reference(number=3))
    @patch("prototype.transcript.load_transcript")
    def test_discovers_policy_when_no_policy_path_is_provided(
        self,
        load_transcript,
        parse_pr_reference,
        build_receipt_prompt,
        generate_receipt,
        get_pull_request_context,
        resolve_repository,
        get_origin_repository,
        load_policy_context,
        get_repository_root,
        tmp_path,
    ):
        transcript_path = tmp_path / "transcript.txt"
        transcript_path.write_text("content\n", encoding="utf-8")
        policy = policy_context(
            status="discovered", path=tmp_path / "AI_POLICY.md", content="Policy text."
        )
        load_transcript.return_value = SimpleNamespace(
            path=transcript_path, mode="text", content="content"
        )
        get_repository_root.return_value = tmp_path
        load_policy_context.return_value = policy
        get_pull_request_context.return_value = pr_context()
        generate_receipt.return_value = receipt_result()

        result = CliRunner().invoke(cli, [str(transcript_path), "--pr", "3"])

        assert result.exit_code == 0
        get_repository_root.assert_called_once_with()
        load_policy_context.assert_called_once_with(None, tmp_path)
        build_receipt_prompt.assert_called_once()

    def test_missing_policy_path_fails_before_command_execution(self, tmp_path):
        transcript_path = tmp_path / "transcript.txt"
        transcript_path.write_text("content\n", encoding="utf-8")
        missing_policy = tmp_path / "missing-policy.md"

        result = CliRunner().invoke(
            cli,
            [str(transcript_path), "--pr", "3", "--policy", str(missing_policy)],
        )

        assert result.exit_code != 0
        assert "does not exist" in result.output


class TestCliErrors:
    @patch("prototype.cli.resolve_repository", return_value="owner/repo")
    @patch("prototype.cli.get_pull_request_context")
    @patch(
        "prototype.cli.generate_receipt",
        side_effect=LLMClientError("OPENAI_API_KEY is required to generate a receipt"),
    )
    @patch("prototype.cli.build_receipt_prompt", return_value="receipt prompt")
    @patch("prototype.cli.parse_pr_reference", return_value=pr_reference(number=3))
    @patch("prototype.transcript.load_transcript")
    def test_reports_llm_client_errors(
        self,
        load_transcript,
        parse_pr_reference,
        build_receipt_prompt,
        generate_receipt,
        get_pull_request_context,
        resolve_repository,
        tmp_path,
    ):
        get_pull_request_context.return_value = pr_context()
        transcript_path = tmp_path / "transcript.txt"
        transcript_path.write_text("content\n", encoding="utf-8")

        result = CliRunner().invoke(cli, [str(transcript_path), "--pr", "3"])

        assert result.exit_code != 0
        build_receipt_prompt.assert_called_once()
        generate_receipt.assert_called_once_with("receipt prompt")
        assert "OPENAI_API_KEY is required to generate a receipt" in result.output

    @patch("prototype.cli.validate_repo", return_value="option-owner/option-repo")
    @patch(
        "prototype.cli.resolve_repository",
        side_effect=GitHubContextError("repository mismatch"),
    )
    @patch(
        "prototype.cli.parse_pr_reference",
        return_value=pr_reference(number=3, repo="url-owner/url-repo"),
    )
    @patch("prototype.transcript.load_transcript")
    def test_reports_repository_resolution_errors(
        self,
        load_transcript,
        parse_pr_reference,
        resolve_repository,
        validate_repo,
        tmp_path,
    ):
        transcript_path = tmp_path / "transcript.txt"
        transcript_path.write_text("content\n", encoding="utf-8")

        result = CliRunner().invoke(
            cli,
            [
                str(transcript_path),
                "--pr",
                "https://github.com/url-owner/url-repo/pull/3",
                "--repo",
                "option-owner/option-repo",
            ],
        )

        assert result.exit_code != 0
        assert "repository mismatch" in result.output

    @patch(
        "prototype.cli.resolve_repository",
        side_effect=GitHubContextError('pass "--repo owner/name"'),
    )
    @patch("prototype.cli.parse_pr_reference", return_value=pr_reference(number=3))
    @patch("prototype.transcript.load_transcript")
    def test_fails_when_repository_cannot_be_resolved(
        self,
        load_transcript,
        parse_pr_reference,
        resolve_repository,
        tmp_path,
    ):
        transcript_path = tmp_path / "transcript.txt"
        transcript_path.write_text("content\n", encoding="utf-8")

        result = CliRunner().invoke(cli, [str(transcript_path), "--pr", "3"])

        assert result.exit_code != 0
        assert 'pass "--repo owner/name"' in result.output

    def test_missing_pr_fails_with_required_option_error(self, tmp_path):
        transcript_path = tmp_path / "transcript.txt"
        transcript_path.write_text("content\n", encoding="utf-8")

        result = CliRunner().invoke(cli, [str(transcript_path)])

        assert result.exit_code != 0
        assert "Missing option '--pr'" in result.output

    def test_invalid_pr_fails_with_actionable_message(self, tmp_path):
        transcript_path = tmp_path / "transcript.txt"
        transcript_path.write_text("content\n", encoding="utf-8")

        with patch(
            "prototype.cli.parse_pr_reference",
            side_effect=GitHubContextError(
                "PR must be a positive integer or GitHub PR URL"
            ),
        ):
            result = CliRunner().invoke(cli, [str(transcript_path), "--pr", "not-a-pr"])

        assert result.exit_code != 0
        assert "PR must be a positive integer or GitHub PR URL" in result.output

    def test_invalid_issue_fails_with_actionable_message(self, tmp_path):
        transcript_path = tmp_path / "transcript.txt"
        transcript_path.write_text("content\n", encoding="utf-8")

        with patch(
            "prototype.cli.parse_issue_reference",
            side_effect=GitHubContextError(
                "issue must be a positive integer or GitHub issue URL"
            ),
        ):
            result = CliRunner().invoke(
                cli,
                [str(transcript_path), "--pr", "3", "--issue", "not-an-issue"],
            )

        assert result.exit_code != 0
        assert "issue must be a positive integer or GitHub issue URL" in result.output

    @patch("prototype.cli.resolve_repository", return_value="owner/repo")
    @patch("prototype.cli.get_pull_request_context")
    @patch("prototype.cli.get_issue_context")
    @patch(
        "prototype.cli.parse_issue_reference",
        return_value=issue_reference(number=1, repo="other/repo"),
    )
    @patch("prototype.cli.parse_pr_reference", return_value=pr_reference(number=3))
    @patch("prototype.transcript.load_transcript")
    def test_issue_url_repository_mismatch_fails(
        self,
        load_transcript,
        parse_pr_reference,
        parse_issue_reference,
        get_issue_context,
        get_pull_request_context,
        resolve_repository,
        tmp_path,
    ):
        transcript_path = tmp_path / "transcript.txt"
        transcript_path.write_text("content\n", encoding="utf-8")

        result = CliRunner().invoke(
            cli,
            [
                str(transcript_path),
                "--pr",
                "3",
                "--issue",
                "https://github.com/other/repo/issues/1",
            ],
        )

        assert result.exit_code != 0
        parse_pr_reference.assert_called_once_with("3")
        parse_issue_reference.assert_called_once_with("https://github.com/other/repo/issues/1")
        assert 'issue URL repository "other/repo" does not match repository "owner/repo"' in result.output
        get_pull_request_context.assert_not_called()
        get_issue_context.assert_not_called()

    def test_missing_transcript_path_fails_before_command_execution(self, tmp_path):
        missing_path = tmp_path / "missing.txt"

        result = CliRunner().invoke(cli, [str(missing_path), "--pr", "3"])

        assert result.exit_code != 0
        assert "does not exist" in result.output
        assert "BuiltWithAi PR Ownership Receipt" not in result.output
