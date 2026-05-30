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
from prototype.render import render_private_evaluation, render_public_receipt
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
@click.option(
    "--show-private-eval",
    is_flag=True,
    help="Print the private heuristic evaluation after the public receipt.",
)
@click.option(
    "--receipt-output",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Write the public receipt markdown to this file instead of stdout.",
)
@click.option(
    "--private-eval-output",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Write the private heuristic evaluation JSON to this file.",
)
@click.option(
    "--overwrite",
    is_flag=True,
    help="Allow overwriting existing output files.",
)
def cli(
    transcript_path,
    pr_number,
    issue_number,
    policy_path,
    repo_name,
    show_private_eval,
    receipt_output,
    private_eval_output,
    overwrite,
):
    if receipt_output is not None and receipt_output.exists() and not overwrite:
        raise click.ClickException(
            f'receipt output file "{receipt_output}" already exists; pass --overwrite to replace it'
        )
    if private_eval_output is not None and private_eval_output.exists() and not overwrite:
        raise click.ClickException(
            f'private evaluation output file "{private_eval_output}" already exists; pass --overwrite to replace it'
        )

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

    private_evaluation_json = render_private_evaluation(receipt_result.private_evaluation)
    if private_eval_output is not None:
        private_eval_output.write_text(private_evaluation_json, encoding="utf-8")

    public_receipt_markdown = render_public_receipt(receipt_result.public_receipt)
    if receipt_output is not None:
        receipt_output.write_text(public_receipt_markdown, encoding="utf-8")
    else:
        click.echo(public_receipt_markdown, nl=False)
    if show_private_eval:
        click.echo("\nPrivate heuristic evaluation\n")
        click.echo(private_evaluation_json, nl=False)


if __name__ == "__main__":
    cli()
