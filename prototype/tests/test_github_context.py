from unittest.mock import patch

import pytest

from prototype.github_context import (
    GitHubContextError,
    PullRequestContext,
    PullRequestReference,
    get_pull_request_context,
    parse_github_remote,
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

    def test_reports_missing_pr_readably(self, github_class, monkeypatch):
        monkeypatch.setenv("GITHUB_TOKEN", "secret-token")
        repo = github_class.return_value.get_repo.return_value
        repo.get_pull.side_effect = self.GitHubError(404, "Not Found")

        with pytest.raises(
            GitHubContextError,
            match="could not find PR #99 in owner/repo",
        ):
            get_pull_request_context("owner/repo", 99)
