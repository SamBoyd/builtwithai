from pathlib import Path

import click

from prototype.github_context import (
    GitHubContextError,
    get_issue_context,
    get_origin_repository,
    get_pull_request_context,
    parse_issue_reference,
    parse_pr_reference,
    resolve_repository,
    validate_repo,
)
from prototype.llm_client import LLMClientError, generate_receipt
from prototype.policy import PolicyContextError, get_repository_root, load_policy_context
from prototype.prompt import build_receipt_prompt
from prototype.render import render_public_receipt
from prototype import transcript


def parse_pr(ctx, param, value):
    try:
        return parse_pr_reference(value)
    except GitHubContextError as error:
        raise click.BadParameter(str(error)) from error


def parse_issue(ctx, param, value):
    if value is None:
        return None
    try:
        return parse_issue_reference(value)
    except GitHubContextError as error:
        raise click.BadParameter(str(error)) from error


def parse_repo(ctx, param, value):
    if value is None:
        return None
    try:
        return validate_repo(value)
    except GitHubContextError as error:
        raise click.BadParameter(str(error)) from error


@click.command()
@click.argument(
    "transcript_path",
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
    metavar="TRANSCRIPT_PATH",
)
@click.option("--pr", "pr_number", required=True, callback=parse_pr, help="PR number or GitHub PR URL.")
@click.option("--issue", "issue_number", callback=parse_issue, help="Issue number or GitHub issue URL.")
@click.option(
    "--policy",
    "policy_path",
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
    help="Repository AI or contribution policy file.",
)
@click.option("--repo", "repo_name", callback=parse_repo, help='GitHub repository in "owner/name" format.')
def cli(transcript_path, pr_number, issue_number, policy_path, repo_name):
    loaded_transcript = transcript.load_transcript(transcript_path)
    try:
        repository = resolve_repository(pr_number.repo, repo_name, get_origin_repository)
        if issue_number is not None:
            if issue_number.repo and issue_number.repo != repository:
                raise GitHubContextError(
                    f'issue URL repository "{issue_number.repo}" does not match repository "{repository}"'
                )
        pr_context = get_pull_request_context(repository, pr_number.number)
        issue_context = None
        if issue_number is not None:
            issue_context = get_issue_context(repository, issue_number.number)
    except GitHubContextError as error:
        raise click.ClickException(str(error)) from error

    try:
        policy_context = load_policy_context(policy_path, get_repository_root())
    except PolicyContextError as error:
        raise click.ClickException(str(error)) from error

    prompt = build_receipt_prompt(
        loaded_transcript,
        pr_context,
        issue_context=issue_context,
        policy_context=policy_context,
    )
    try:
        receipt_result = generate_receipt(prompt)
    except LLMClientError as error:
        raise click.ClickException(str(error)) from error

    click.echo(render_public_receipt(receipt_result.public_receipt), nl=False)


if __name__ == "__main__":
    cli()
