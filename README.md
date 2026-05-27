# BuiltWithAI

## Prototype CLI

Run the prototype CLI as a Python module from the repository root:

```bash
python3 -m prototype.cli prototype/spec.md --pr 3
```

Do not run it as `python3 prototype/cli.py`; module execution keeps package imports clean until the project has a packaged console script.

### GitHub token

The CLI reads GitHub API credentials from `GITHUB_TOKEN`.

```bash
export GITHUB_TOKEN=github_pat_...
python3 -m prototype.cli transcript.txt --pr 3 --repo owner/name
```

Public repositories may work without a token, but GitHub rate limits are lower and private repositories require one. Use a fine-grained personal access token with the narrowest practical access:

- Repository access: only the target repository.
- Metadata: read-only.
- Pull requests: read-only.
- Issues: read-only, for the later issue-context step.
- Contents: read-only, for later policy-file discovery.

The prototype does not need write permissions. Do not grant comment, push, workflow, administration, secrets, or repository write access.
