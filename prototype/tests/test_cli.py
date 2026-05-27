from types import SimpleNamespace
from unittest.mock import patch

from click.testing import CliRunner

from prototype.cli import GitHubContextError, cli


def pr_reference(number=3, repo=None):
    return SimpleNamespace(number=number, repo=repo)


def pr_context(number=3, title="Add receipt context", body="", url=None, head_sha="abc123"):
    return SimpleNamespace(
        number=number,
        title=title,
        body=body,
        url=url or f"https://github.com/owner/repo/pull/{number}",
        head_sha=head_sha,
    )


def test_help_shows_required_cli_surface():
    result = CliRunner().invoke(cli, ["--help"])

    assert result.exit_code == 0
    assert "TRANSCRIPT_PATH" in result.output
    assert "--pr" in result.output
    assert "--repo" in result.output


@patch("prototype.cli.get_origin_repository", return_value="owner/repo")
@patch("prototype.cli.resolve_repository", return_value="owner/repo")
@patch("prototype.cli.get_pull_request_context")
@patch("prototype.cli.parse_pr_reference", return_value=pr_reference(number=3))
@patch("prototype.transcript.load_transcript")
def test_numeric_pr_succeeds_with_transcript_file(
    load_transcript,
    parse_pr_reference,
    get_pull_request_context,
    resolve_repository,
    get_origin_repository,
    tmp_path,
):
    get_pull_request_context.return_value = pr_context(body="Do not print me")
    transcript_path = tmp_path / "transcript.txt"
    transcript_path.write_text("user: please make the change\n", encoding="utf-8")

    result = CliRunner().invoke(cli, [str(transcript_path), "--pr", "3"])

    assert result.exit_code == 0
    parse_pr_reference.assert_called_once_with("3")
    load_transcript.assert_called_once_with(transcript_path)
    resolve_repository.assert_called_once_with(None, None, get_origin_repository)
    get_pull_request_context.assert_called_once_with("owner/repo", 3)
    assert "BuiltWithAi PR Ownership Receipt" in result.output
    assert "Status: Caution" in result.output
    assert "Transcript and GitHub PR metadata." in result.output
    assert "PR #3: Add receipt context (https://github.com/owner/repo/pull/3) at abc123." in result.output
    assert "Do not print me" not in result.output
    assert "Transcript:" not in result.output


@patch("prototype.transcript.load_transcript")
@patch("prototype.cli.get_origin_repository", return_value="owner/repo")
@patch("prototype.cli.resolve_repository", return_value="owner/repo")
@patch("prototype.cli.get_pull_request_context")
@patch("prototype.cli.parse_pr_reference", return_value=pr_reference(number=3))
def test_cli_loads_transcript_path(
    parse_pr_reference,
    get_pull_request_context,
    resolve_repository,
    get_origin_repository,
    load_transcript,
    tmp_path,
):
    transcript_path = tmp_path / "transcript.txt"
    transcript_path.write_text("user: please make the change\n", encoding="utf-8")
    load_transcript.return_value = SimpleNamespace(path=transcript_path, mode="text", content="content")
    get_pull_request_context.return_value = pr_context()

    result = CliRunner().invoke(cli, [str(transcript_path), "--pr", "3"])

    assert result.exit_code == 0
    load_transcript.assert_called_once_with(transcript_path)


@patch("prototype.cli.resolve_repository", return_value="owner/repo")
@patch("prototype.cli.get_pull_request_context")
@patch("prototype.cli.parse_pr_reference", return_value=pr_reference(number=17, repo="owner/repo"))
@patch("prototype.transcript.load_transcript")
def test_github_pr_url_succeeds_and_extracts_number(
    load_transcript,
    parse_pr_reference,
    get_pull_request_context,
    resolve_repository,
    tmp_path,
):
    get_pull_request_context.return_value = pr_context(number=17, title="Add URL parsing", head_sha="def456")
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
    assert "BuiltWithAi PR Ownership Receipt" in result.output
    assert "Status: Caution" in result.output


@patch("prototype.cli.validate_repo", return_value="owner/repo")
@patch("prototype.cli.resolve_repository", return_value="owner/repo")
@patch("prototype.cli.get_pull_request_context")
@patch("prototype.cli.parse_pr_reference", return_value=pr_reference(number=3))
@patch("prototype.transcript.load_transcript")
def test_cli_uses_repo_option_for_numeric_pr(
    load_transcript,
    parse_pr_reference,
    get_pull_request_context,
    resolve_repository,
    validate_repo,
    tmp_path,
):
    get_pull_request_context.return_value = pr_context()
    transcript_path = tmp_path / "transcript.txt"
    transcript_path.write_text("content\n", encoding="utf-8")

    result = CliRunner().invoke(cli, [str(transcript_path), "--pr", "3", "--repo", "owner/repo"])

    assert result.exit_code == 0
    validate_repo.assert_called_once_with("owner/repo")
    resolve_repository.assert_called_once()
    get_pull_request_context.assert_called_once_with("owner/repo", 3)


@patch("prototype.cli.resolve_repository", return_value="owner/repo")
@patch("prototype.cli.get_pull_request_context")
@patch("prototype.cli.parse_pr_reference", return_value=pr_reference(number=42))
@patch("prototype.transcript.load_transcript")
def test_cli_interpolates_receipt_binding_from_pr_context(
    load_transcript,
    parse_pr_reference,
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
    transcript_path = tmp_path / "transcript.txt"
    transcript_path.write_text("content\n", encoding="utf-8")

    result = CliRunner().invoke(cli, [str(transcript_path), "--pr", "42"])

    assert result.exit_code == 0
    assert (
        "Receipt binding: PR #42: Preserve reviewer intent "
        "(https://github.com/owner/repo/pull/42) at feedface."
    ) in result.output


@patch("prototype.cli.validate_repo", return_value="option-owner/option-repo")
@patch("prototype.cli.resolve_repository", side_effect=GitHubContextError("repository mismatch"))
@patch("prototype.cli.parse_pr_reference", return_value=pr_reference(number=3, repo="url-owner/url-repo"))
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


@patch("prototype.cli.resolve_repository", side_effect=GitHubContextError('pass "--repo owner/name"'))
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
        side_effect=GitHubContextError("PR must be a positive integer or GitHub PR URL"),
    ):
        result = CliRunner().invoke(cli, [str(transcript_path), "--pr", "not-a-pr"])

    assert result.exit_code != 0
    assert "PR must be a positive integer or GitHub PR URL" in result.output


def test_missing_transcript_path_fails_before_command_execution(tmp_path):
    missing_path = tmp_path / "missing.txt"

    result = CliRunner().invoke(cli, [str(missing_path), "--pr", "3"])

    assert result.exit_code != 0
    assert "does not exist" in result.output
    assert "BuiltWithAi PR Ownership Receipt" not in result.output
