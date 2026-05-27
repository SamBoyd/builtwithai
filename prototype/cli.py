from pathlib import Path

import click

from prototype.github_context import (
    GitHubContextError,
    get_origin_repository,
    get_pull_request_context,
    parse_pr_reference,
    resolve_repository,
    validate_repo,
)
from prototype.render import render_public_receipt
from prototype.schemas import PublicReceipt
from prototype import transcript


def parse_pr(ctx, param, value):
    try:
        return parse_pr_reference(value)
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
@click.option("--repo", "repo_name", callback=parse_repo, help='GitHub repository in "owner/name" format.')
def cli(transcript_path, pr_number, repo_name):
    _loaded_transcript = transcript.load_transcript(transcript_path)
    try:
        repository = resolve_repository(pr_number.repo, repo_name, get_origin_repository)
        pr_context = get_pull_request_context(repository, pr_number.number)
    except GitHubContextError as error:
        raise click.ClickException(str(error)) from error

    receipt = PublicReceipt(
        status="Caution",
        policy_fit="",
        human_ownership="",
        ai_role="",
        evidence_reviewed="Transcript and GitHub PR metadata.",
        tests_checks_run="",
        reviewer_attention_requested="",
        known_risks_or_unknowns="",
        recommended_next_step="",
        receipt_binding=(
            f"PR #{pr_context.number}: {pr_context.title} ({pr_context.url}) at {pr_context.head_sha}."
        ),
    )

    click.echo(render_public_receipt(receipt), nl=False)


if __name__ == "__main__":
    cli()
