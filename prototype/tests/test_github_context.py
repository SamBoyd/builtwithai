from unittest.mock import patch

import pytest

from prototype.github_context import (
    GitHubContextError,
    IssueContext,
    IssueReference,
    PullRequestContext,
    PullRequestReference,
    get_issue_context,
    get_pull_request_context,
    parse_github_remote,
    parse_issue_reference,
    parse_pr_reference,
    resolve_repository,
)


class TestParsePrReference:
    def test_numeric_pr_reference_has_no_repo(self):
        assert parse_pr_reference("3") == PullRequestReference(number=3, repo=None)

    def test_pr_url_reference_includes_repo(self):
        assert parse_pr_reference("https://github.com/Owner/Repo/pull/17") == PullRequestReference(
            number=17,
            repo="Owner/Repo",
        )

    def test_rejects_invalid_value(self):
        with pytest.raises(GitHubContextError, match="PR must be a positive integer or GitHub PR URL"):
            parse_pr_reference("not-a-pr")


class TestParseIssueReference:
    def test_numeric_issue_reference_has_no_repo(self):
        assert parse_issue_reference("1") == IssueReference(number=1, repo=None)

    def test_issue_url_reference_includes_repo(self):
        assert parse_issue_reference("https://github.com/Owner/Repo/issues/17") == IssueReference(
            number=17,
            repo="Owner/Repo",
        )

    def test_rejects_invalid_value(self):
        with pytest.raises(GitHubContextError, match="issue must be a positive integer or GitHub issue URL"):
            parse_issue_reference("not-an-issue")


class TestParseGithubRemote:
    @pytest.mark.parametrize(
        ("remote_url", "expected"),
        [
            ("git@github.com:OWNER/REPO.git", "OWNER/REPO"),
            ("https://github.com/OWNER/REPO.git", "OWNER/REPO"),
            ("https://github.com/OWNER/REPO", "OWNER/REPO"),
        ],
    )
    def test_supported_shapes(self, remote_url, expected):
        assert parse_github_remote(remote_url) == expected

    def test_rejects_unsupported_shape(self):
        assert parse_github_remote("https://example.com/OWNER/REPO.git") is None


class TestResolveRepository:
    def test_prefers_pr_url_repo(self):
        assert resolve_repository("url-owner/url-repo", "url-owner/url-repo", lambda: None) == "url-owner/url-repo"

    def test_rejects_mismatched_pr_url_and_option_repo(self):
        with pytest.raises(GitHubContextError, match="does not match --repo"):
            resolve_repository("url-owner/url-repo", "option-owner/option-repo", lambda: None)

    def test_uses_option_repo_before_origin(self):
        assert resolve_repository(None, "option-owner/option-repo", lambda: "origin-owner/origin-repo") == (
            "option-owner/option-repo"
        )

    def test_uses_origin_when_needed(self):
        assert resolve_repository(None, None, lambda: "origin-owner/origin-repo") == "origin-owner/origin-repo"

    def test_fails_when_no_repo_available(self):
        with pytest.raises(GitHubContextError, match='pass "--repo owner/name"'):
            resolve_repository(None, None, lambda: None)


@patch("prototype.github_context.Github")
class TestGetPullRequestContext:
    class GitHubError(Exception):
        def __init__(self, status, message):
            super().__init__(message)
            self.status = status

    def configure_pull(
        self,
        github_class,
        *,
        number=3,
        title="Add receipt context",
        body="PR body",
        url="https://github.com/owner/repo/pull/3",
        head_sha="abc123",
    ):
        pull = github_class.return_value.get_repo.return_value.get_pull.return_value
        pull.number = number
        pull.title = title
        pull.body = body
        pull.html_url = url
        pull.head.sha = head_sha
        return pull

    def test_uses_github_token(self, github_class, monkeypatch):
        monkeypatch.setenv("GITHUB_TOKEN", "secret-token")
        github = github_class.return_value
        repo = github.get_repo.return_value
        self.configure_pull(github_class)

        context = get_pull_request_context("owner/repo", 3)

        github_class.assert_called_once_with("secret-token")
        github.get_repo.assert_called_once_with("owner/repo")
        repo.get_pull.assert_called_once_with(3)
        assert context == PullRequestContext(
            number=3,
            title="Add receipt context",
            body="PR body",
            url="https://github.com/owner/repo/pull/3",
            head_sha="abc123",
        )

    def test_allows_missing_github_token(self, github_class, monkeypatch):
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        self.configure_pull(
            github_class,
            number=4,
            title="No token",
            body=None,
            url="https://github.com/owner/repo/pull/4",
            head_sha="def456",
        )

        context = get_pull_request_context("owner/repo", 4)

        github_class.assert_called_once_with()
        assert context.body == ""

    def test_wraps_fetch_errors(self, github_class, monkeypatch):
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        github_class.return_value.get_repo.side_effect = RuntimeError("rate limited")

        with pytest.raises(GitHubContextError, match="set GITHUB_TOKEN"):
            get_pull_request_context("owner/repo", 3)

    def test_reports_authentication_errors_readably(self, github_class, monkeypatch):
        monkeypatch.setenv("GITHUB_TOKEN", "bad-token")
        github_class.return_value.get_repo.side_effect = self.GitHubError(401, "Bad credentials")

        with pytest.raises(
            GitHubContextError,
            match="GitHub authentication failed; check that GITHUB_TOKEN is set to a valid token.",
        ):
            get_pull_request_context("owner/repo", 3)

    def test_reports_inaccessible_repository_readably(self, github_class, monkeypatch):
        monkeypatch.setenv("GITHUB_TOKEN", "secret-token")
        github_class.return_value.get_repo.side_effect = self.GitHubError(404, "Not Found")

        with pytest.raises(
            GitHubContextError,
            match="could not access owner/repo; check the repository name and GITHUB_TOKEN access.",
        ):
            get_pull_request_context("owner/repo", 3)

    def test_reports_missing_pr_readably(self, github_class, monkeypatch):
        monkeypatch.setenv("GITHUB_TOKEN", "secret-token")
        repo = github_class.return_value.get_repo.return_value
        repo.get_pull.side_effect = self.GitHubError(404, "Not Found")

        with pytest.raises(
            GitHubContextError,
            match="could not find PR #99 in owner/repo",
        ):
            get_pull_request_context("owner/repo", 99)

    def test_reports_rate_limit_errors_readably(self, github_class, monkeypatch):
        monkeypatch.setenv("GITHUB_TOKEN", "secret-token")
        github_class.return_value.get_repo.side_effect = self.GitHubError(403, "API rate limit exceeded")

        with pytest.raises(
            GitHubContextError,
            match="GitHub API rate limit exceeded; set GITHUB_TOKEN or wait for the rate limit to reset.",
        ):
            get_pull_request_context("owner/repo", 3)

    def test_reports_permission_errors_readably(self, github_class, monkeypatch):
        monkeypatch.setenv("GITHUB_TOKEN", "secret-token")
        repo = github_class.return_value.get_repo.return_value
        repo.get_pull.side_effect = self.GitHubError(403, "Resource not accessible by personal access token")

        with pytest.raises(
            GitHubContextError,
            match=(
                "GITHUB_TOKEN does not have permission to read PRs for owner/repo; "
                "use a token with read-only Pull requests and Metadata access."
            ),
        ):
            get_pull_request_context("owner/repo", 3)


@patch("prototype.github_context.Github")
class TestGetIssueContext:
    class GitHubError(Exception):
        def __init__(self, status, message):
            super().__init__(message)
            self.status = status

    def configure_issue(
        self,
        github_class,
        *,
        number=1,
        title="Add receipt context",
        body="Issue body",
    ):
        issue = github_class.return_value.get_repo.return_value.get_issue.return_value
        issue.number = number
        issue.title = title
        issue.body = body
        return issue

    def test_uses_github_token(self, github_class, monkeypatch):
        monkeypatch.setenv("GITHUB_TOKEN", "secret-token")
        github = github_class.return_value
        repo = github.get_repo.return_value
        self.configure_issue(github_class)

        context = get_issue_context("owner/repo", 1)

        github_class.assert_called_once_with("secret-token")
        github.get_repo.assert_called_once_with("owner/repo")
        repo.get_issue.assert_called_once_with(1)
        assert context == IssueContext(
            number=1,
            title="Add receipt context",
            body="Issue body",
        )

    def test_allows_missing_github_token(self, github_class, monkeypatch):
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        self.configure_issue(
            github_class,
            number=2,
            title="No token",
            body=None,
        )

        context = get_issue_context("owner/repo", 2)

        github_class.assert_called_once_with()
        assert context.body == ""

    def test_wraps_fetch_errors(self, github_class, monkeypatch):
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        github_class.return_value.get_repo.side_effect = RuntimeError("rate limited")

        with pytest.raises(GitHubContextError, match="set GITHUB_TOKEN"):
            get_issue_context("owner/repo", 1)

    def test_reports_authentication_errors_readably(self, github_class, monkeypatch):
        monkeypatch.setenv("GITHUB_TOKEN", "bad-token")
        github_class.return_value.get_repo.side_effect = self.GitHubError(401, "Bad credentials")

        with pytest.raises(
            GitHubContextError,
            match="GitHub authentication failed; check that GITHUB_TOKEN is set to a valid token.",
        ):
            get_issue_context("owner/repo", 1)

    def test_reports_inaccessible_repository_readably(self, github_class, monkeypatch):
        monkeypatch.setenv("GITHUB_TOKEN", "secret-token")
        github_class.return_value.get_repo.side_effect = self.GitHubError(404, "Not Found")

        with pytest.raises(
            GitHubContextError,
            match="could not access owner/repo; check the repository name and GITHUB_TOKEN access.",
        ):
            get_issue_context("owner/repo", 1)

    def test_reports_missing_issue_readably(self, github_class, monkeypatch):
        monkeypatch.setenv("GITHUB_TOKEN", "secret-token")
        repo = github_class.return_value.get_repo.return_value
        repo.get_issue.side_effect = self.GitHubError(404, "Not Found")

        with pytest.raises(
            GitHubContextError,
            match="could not find issue #99 in owner/repo",
        ):
            get_issue_context("owner/repo", 99)

    def test_reports_rate_limit_errors_readably(self, github_class, monkeypatch):
        monkeypatch.setenv("GITHUB_TOKEN", "secret-token")
        github_class.return_value.get_repo.side_effect = self.GitHubError(403, "API rate limit exceeded")

        with pytest.raises(
            GitHubContextError,
            match="GitHub API rate limit exceeded; set GITHUB_TOKEN or wait for the rate limit to reset.",
        ):
            get_issue_context("owner/repo", 1)

    def test_reports_permission_errors_readably(self, github_class, monkeypatch):
        monkeypatch.setenv("GITHUB_TOKEN", "secret-token")
        repo = github_class.return_value.get_repo.return_value
        repo.get_issue.side_effect = self.GitHubError(403, "Resource not accessible by personal access token")

        with pytest.raises(
            GitHubContextError,
            match=(
                "GITHUB_TOKEN does not have permission to read issues for owner/repo; "
                "use a token with read-only Issues and Metadata access."
            ),
        ):
            get_issue_context("owner/repo", 1)
