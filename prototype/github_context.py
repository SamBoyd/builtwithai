import os
import re
import subprocess
from dataclasses import dataclass

try:
    from github import Github
except ImportError:  # pragma: no cover - exercised only when dependency is absent.
    Github = None


_GITHUB_PR_URL_RE = re.compile(
    r"^https://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/pull/(?P<number>[1-9][0-9]*)/?$"
)
_GITHUB_REPO_RE = re.compile(r"^[^/\s]+/[^/\s]+$")
_SSH_REMOTE_RE = re.compile(r"^git@github\.com:(?P<repo>[^/]+/[^/]+?)(?:\.git)?$")
_HTTPS_REMOTE_RE = re.compile(r"^https://github\.com/(?P<repo>[^/]+/[^/]+?)(?:\.git)?$")


class GitHubContextError(Exception):
    pass


@dataclass(frozen=True)
class PullRequestReference:
    number: int
    repo: str | None


@dataclass(frozen=True)
class PullRequestContext:
    number: int
    title: str
    body: str
    url: str
    head_sha: str


def parse_pr_reference(value: str) -> PullRequestReference:
    if value.isdigit():
        pr_number = int(value)
        if pr_number > 0:
            return PullRequestReference(number=pr_number, repo=None)

    match = _GITHUB_PR_URL_RE.match(value)
    if match:
        return PullRequestReference(
            number=int(match.group("number")),
            repo=f"{match.group('owner')}/{match.group('repo')}",
        )

    raise GitHubContextError("PR must be a positive integer or GitHub PR URL")


def validate_repo(value: str) -> str:
    if not _GITHUB_REPO_RE.match(value):
        raise GitHubContextError('repository must use "owner/name" format')
    return value


def parse_github_remote(remote_url: str) -> str | None:
    for pattern in (_SSH_REMOTE_RE, _HTTPS_REMOTE_RE):
        match = pattern.match(remote_url)
        if match:
            return match.group("repo")
    return None


def get_origin_repository() -> str | None:
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return None

    if result.returncode != 0:
        return None
    return parse_github_remote(result.stdout.strip())


def resolve_repository(
    pr_repo: str | None,
    option_repo: str | None,
    origin_repository_loader=get_origin_repository,
) -> str:
    if pr_repo and option_repo and pr_repo != option_repo:
        raise GitHubContextError(f'PR URL repository "{pr_repo}" does not match --repo "{option_repo}"')
    if pr_repo:
        return pr_repo
    if option_repo:
        return validate_repo(option_repo)

    origin_repo = origin_repository_loader()
    if origin_repo:
        return origin_repo

    raise GitHubContextError('could not infer GitHub repository; pass "--repo owner/name"')


def get_pull_request_context(repo: str, pr_number: int) -> PullRequestContext:
    if Github is None:
        raise GitHubContextError("PyGithub is required to fetch GitHub PR context")

    token = os.environ.get("GITHUB_TOKEN")
    github_client = Github(token) if token else Github()

    try:
        pull = github_client.get_repo(repo).get_pull(pr_number)
    except Exception as error:
        if getattr(error, "status", None) == 404:
            raise GitHubContextError(
                f"could not find PR #{pr_number} in {repo}; check the PR number and repository"
            ) from error
        if token:
            raise GitHubContextError(f"could not fetch GitHub PR context: {error}") from error
        raise GitHubContextError(
            f"could not fetch GitHub PR context: {error}. For private repositories or rate limits, set GITHUB_TOKEN."
        ) from error

    return PullRequestContext(
        number=pull.number,
        title=pull.title,
        body=pull.body or "",
        url=pull.html_url,
        head_sha=pull.head.sha,
    )
