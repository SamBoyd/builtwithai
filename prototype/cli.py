#!/usr/bin/env python3

import re
from pathlib import Path

import click

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

    click.echo(f"Transcript: {loaded_transcript.path}")
    click.echo(f"PR: {pr_number}")


if __name__ == "__main__":
    cli()
