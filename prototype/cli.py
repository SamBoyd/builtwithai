#!/usr/bin/env python3

import re
from pathlib import Path

import click

from prototype.render import render_public_receipt
from prototype.schemas import PublicReceipt
from prototype import transcript


_GITHUB_PR_URL_RE = re.compile(
    r"^https://github\.com/[^/]+/[^/]+/pull/(?P<number>[1-9][0-9]*)/?$"
)


def parse_pr(ctx, param, value):
    if value.isdigit():
        pr_number = int(value)
        if pr_number > 0:
            return pr_number

    match = _GITHUB_PR_URL_RE.match(value)
    if match:
        return int(match.group("number"))

    raise click.BadParameter("PR must be a positive integer or GitHub PR URL")


@click.command()
@click.argument(
    "transcript_path",
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=Path),
    metavar="TRANSCRIPT_PATH",
)
@click.option("--pr", "pr_number", required=True, callback=parse_pr, help="PR number or GitHub PR URL.")
def cli(transcript_path, pr_number):
    loaded_transcript = transcript.load_transcript(transcript_path)
    receipt = PublicReceipt(
        status="Caution",
        policy_fit="",
        human_ownership="",
        ai_role="",
        evidence_reviewed="",
        tests_checks_run="",
        reviewer_attention_requested="",
        known_risks_or_unknowns="",
        recommended_next_step="",
        receipt_binding="",
    )

    click.echo(render_public_receipt(receipt), nl=False)


if __name__ == "__main__":
    cli()
