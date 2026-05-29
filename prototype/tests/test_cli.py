from types import SimpleNamespace
from unittest.mock import patch

from click.testing import CliRunner

from prototype.cli import GitHubContextError, cli
from prototype.llm_client import LLMClientError
from prototype.schemas import PublicReceipt, ReceiptResult, ReceiptStatus


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
        )
    )


def test_help_shows_required_cli_surface():
    result = CliRunner().invoke(cli, ["--help"])

    assert result.exit_code == 0
    assert "TRANSCRIPT_PATH" in result.output
    assert "--pr" in result.output
    assert "--issue" in result.output
    assert "--repo" in result.output


@patch("prototype.cli.get_origin_repository", return_value="owner/repo")
@patch("prototype.cli.resolve_repository", return_value="owner/repo")
@patch("prototype.cli.get_pull_request_context")
@patch("prototype.cli.generate_receipt")
@patch("prototype.cli.build_receipt_prompt", return_value="secret prompt")
@patch("prototype.cli.parse_pr_reference", return_value=pr_reference(number=3))
@patch("prototype.transcript.load_transcript")
def test_numeric_pr_succeeds_with_transcript_file(
    load_transcript,
    parse_pr_reference,
    build_receipt_prompt,
    generate_receipt,
    get_pull_request_context,
    resolve_repository,
    get_origin_repository,
    tmp_path,
):
    loaded_transcript = SimpleNamespace(
        path=tmp_path / "transcript.txt", mode="text", content="user secret"
    )
    pr = pr_context(body="Do not print me")
    load_transcript.return_value = loaded_transcript
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
    build_receipt_prompt.assert_called_once_with(loaded_transcript, pr)
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


@patch("prototype.transcript.load_transcript")
@patch("prototype.cli.get_origin_repository", return_value="owner/repo")
@patch("prototype.cli.resolve_repository", return_value="owner/repo")
@patch("prototype.cli.get_pull_request_context")
@patch("prototype.cli.generate_receipt")
@patch("prototype.cli.build_receipt_prompt", return_value="receipt prompt")
@patch("prototype.cli.parse_pr_reference", return_value=pr_reference(number=3))
def test_cli_loads_transcript_path(
    parse_pr_reference,
    build_receipt_prompt,
    generate_receipt,
    get_pull_request_context,
    resolve_repository,
    get_origin_repository,
    load_transcript,
    tmp_path,
):
    transcript_path = tmp_path / "transcript.txt"
    transcript_path.write_text("user: please make the change\n", encoding="utf-8")
    loaded_transcript = SimpleNamespace(
        path=transcript_path, mode="text", content="content"
    )
    pr = pr_context()
    load_transcript.return_value = loaded_transcript
    get_pull_request_context.return_value = pr
    generate_receipt.return_value = receipt_result()

    result = CliRunner().invoke(cli, [str(transcript_path), "--pr", "3"])

    assert result.exit_code == 0
    load_transcript.assert_called_once_with(transcript_path)
    build_receipt_prompt.assert_called_once_with(loaded_transcript, pr)
    generate_receipt.assert_called_once_with("receipt prompt")


@patch("prototype.cli.get_origin_repository", return_value="owner/repo")
@patch("prototype.cli.resolve_repository", return_value="owner/repo")
@patch("prototype.cli.get_issue_context")
@patch("prototype.cli.get_pull_request_context")
@patch("prototype.cli.generate_receipt")
@patch("prototype.cli.build_receipt_prompt", return_value="receipt prompt")
@patch("prototype.cli.parse_issue_reference", return_value=issue_reference(number=1))
@patch("prototype.cli.parse_pr_reference", return_value=pr_reference(number=3))
@patch("prototype.transcript.load_transcript")
def test_cli_fetches_explicit_issue_context(
    load_transcript,
    parse_pr_reference,
    parse_issue_reference,
    build_receipt_prompt,
    generate_receipt,
    get_pull_request_context,
    get_issue_context,
    resolve_repository,
    get_origin_repository,
    tmp_path,
):
    loaded_transcript = SimpleNamespace(
        path=tmp_path / "transcript.txt", mode="text", content="content"
    )
    pr = pr_context()
    issue = issue_context(number=1, title="Original request")
    load_transcript.return_value = loaded_transcript
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
    build_receipt_prompt.assert_called_once_with(loaded_transcript, pr, issue)
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
def test_cli_uses_repo_option_for_numeric_pr(
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
def test_cli_renders_llm_receipt_binding(
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


@patch("prototype.cli.resolve_repository", return_value="owner/repo")
@patch("prototype.cli.get_pull_request_context")
@patch(
    "prototype.cli.generate_receipt",
    side_effect=LLMClientError("OPENAI_API_KEY is required to generate a receipt"),
)
@patch("prototype.cli.build_receipt_prompt", return_value="receipt prompt")
@patch("prototype.cli.parse_pr_reference", return_value=pr_reference(number=3))
@patch("prototype.transcript.load_transcript")
def test_cli_reports_llm_client_errors(
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
def test_cli_reports_repository_resolution_errors(
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
def test_cli_fails_when_repository_cannot_be_resolved(
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


def test_missing_pr_fails_with_required_option_error(tmp_path):
    transcript_path = tmp_path / "transcript.txt"
    transcript_path.write_text("content\n", encoding="utf-8")

    result = CliRunner().invoke(cli, [str(transcript_path)])

    assert result.exit_code != 0
    assert "Missing option '--pr'" in result.output


def test_invalid_pr_fails_with_actionable_message(tmp_path):
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


def test_invalid_issue_fails_with_actionable_message(tmp_path):
    transcript_path = tmp_path / "transcript.txt"
    transcript_path.write_text("content\n", encoding="utf-8")

    with patch(
        "prototype.cli.parse_issue_reference",
        side_effect=GitHubContextError("issue must be a positive integer or GitHub issue URL"),
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
@patch("prototype.cli.parse_issue_reference", return_value=issue_reference(number=1, repo="other/repo"))
@patch("prototype.cli.parse_pr_reference", return_value=pr_reference(number=3))
@patch("prototype.transcript.load_transcript")
def test_issue_url_repository_mismatch_fails(
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


def test_missing_transcript_path_fails_before_command_execution(tmp_path):
    missing_path = tmp_path / "missing.txt"

    result = CliRunner().invoke(cli, [str(missing_path), "--pr", "3"])

    assert result.exit_code != 0
    assert "does not exist" in result.output
    assert "BuiltWithAi PR Ownership Receipt" not in result.output
