from click.testing import CliRunner

from prototype.cli import cli


def test_help_shows_required_cli_surface():
    result = CliRunner().invoke(cli, ["--help"])

    assert result.exit_code == 0
    assert "TRANSCRIPT_PATH" in result.output
    assert "--pr" in result.output


def test_numeric_pr_succeeds_with_transcript_file(tmp_path):
    transcript_path = tmp_path / "transcript.txt"
    transcript_path.write_text("user: please make the change\n", encoding="utf-8")

    result = CliRunner().invoke(cli, [str(transcript_path), "--pr", "3"])

    assert result.exit_code == 0
    assert f"Transcript: {transcript_path}" in result.output
    assert "PR: 3" in result.output


def test_github_pr_url_succeeds_and_extracts_number(tmp_path):
    transcript_path = tmp_path / "transcript.txt"
    transcript_path.write_text("assistant: done\n", encoding="utf-8")

    result = CliRunner().invoke(
        cli,
        [str(transcript_path), "--pr", "https://github.com/owner/repo/pull/17"],
    )

    assert result.exit_code == 0
    assert "PR: 17" in result.output


def test_missing_pr_fails_with_required_option_error(tmp_path):
    transcript_path = tmp_path / "transcript.txt"
    transcript_path.write_text("content\n", encoding="utf-8")

    result = CliRunner().invoke(cli, [str(transcript_path)])

    assert result.exit_code != 0
    assert "Missing option '--pr'" in result.output


def test_invalid_pr_fails_with_actionable_message(tmp_path):
    transcript_path = tmp_path / "transcript.txt"
    transcript_path.write_text("content\n", encoding="utf-8")

    result = CliRunner().invoke(cli, [str(transcript_path), "--pr", "not-a-pr"])

    assert result.exit_code != 0
    assert "PR must be a positive integer or GitHub PR URL" in result.output


def test_missing_transcript_path_fails_before_command_execution(tmp_path):
    missing_path = tmp_path / "missing.txt"

    result = CliRunner().invoke(cli, [str(missing_path), "--pr", "3"])

    assert result.exit_code != 0
    assert "does not exist" in result.output
    assert "Transcript:" not in result.output
