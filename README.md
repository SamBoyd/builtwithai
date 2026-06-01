# BuiltWithAI

BuiltWithAI is an early proposal and prototype for making the human work behind AI-assisted open-source contributions visible again.

AI can help a capable person explore, draft, test, translate, and accelerate work they genuinely understand. It becomes costly when plausible-looking generated work crosses a community boundary and asks maintainers to spend scarce review attention figuring out whether a human did the thinking.

BuiltWithAI allows contributors to attach a ownership statement to the work they submit, which says:

> This was built with AI assistance, but a human reviewed it, made the important judgments, understands the limits, and stands behind the work.

## Why This Exists

The old signal broke.

Before AI, a non-trivial pull request usually meant someone had spent real time with a project. That was never proof of competence or good faith, but effort filtered out a lot. Now a pull request can be one prompt away. A bug report can sound serious without a reproduction. A technical post can imitate expertise without substance. A security report can force maintainers to prove a negative.

Generation got cheap. Review did not.

Open-source communities are responding in different ways: some ban or presumptively reject generated work, some gate participation with stronger rules, and some allow AI-assisted contributions only when the contributor clearly owns the result. Those responses are rational, but fragmented.

BuiltWithAI explores the missing middle between blanket rejection and blind acceptance. It gives careful contributors a way to show what they personally reviewed, changed, tested, rejected, and can explain. It gives maintainers a compact artifact for asking the question that matters:

> Has a capable human taken responsibility for this specific artifact, and will they stay engaged when review begins?

The goal is not to prove correctness, detect AI, or bypass a project's local policy. The goal is to make visible what ownership is present, what evidence was reviewed, what is missing, and what should happen next.

## Prototype CLI

The prototype reads a transcript and GitHub PR metadata, then asks an Instructor-supported LLM for a public BuiltWithAI PR Ownership Receipt.

Run CLI modules from the repository root with `python3 -m prototype.cli`, not by executing `prototype/cli.py` directly.

### Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r prototype/requirements.txt
```

Create a local `.env` file before generating receipts:

```bash
cp .env.example .env
```

Then choose exactly one `LLM_MODEL` line in `.env` and set the matching provider API key. The model value must use Instructor's `provider/model-name` format:

```dotenv
LLM_MODEL=anthropic/claude-sonnet-4-0-20250514
ANTHROPIC_API_KEY=...
```

The `.env.example` file includes commented alternatives for OpenAI, Google, and Groq. Set `GITHUB_TOKEN` too when working with private repositories or when public API rate limits are not enough:

```dotenv
GITHUB_TOKEN=github_pat_...
```

If `LLM_MODEL` is not set, the prototype defaults to `openai/gpt-5.5` and requires `OPENAI_API_KEY`. Exported shell environment variables override values in `.env`.

The prototype only needs read access. Prefer a fine-grained GitHub token scoped to the target repository with read-only Metadata, Pull requests, Issues, and Contents access. It does not need permission to comment, push, administer repositories, manage workflows, or read secrets.

### Usage

```bash
python3 -m prototype.cli TRANSCRIPT_PATH --pr 3 --repo owner/name
```

Examples:

```bash
python3 -m prototype.cli transcript.txt --pr 3 --repo owner/name
python3 -m prototype.cli transcript.txt --pr https://github.com/owner/name/pull/3
python3 -m prototype.cli transcript.txt --pr 3 --issue 1 --repo owner/name
python3 -m prototype.cli transcript.txt --pr 3 --policy AI_POLICY.md --repo owner/name
```

By default, the public receipt is printed to stdout. Optional outputs:

```bash
python3 -m prototype.cli transcript.txt \
  --pr 3 \
  --repo owner/name \
  --receipt-output receipt.md \
  --private-eval-output private-eval.json
```

Use `--show-private-eval` to print the private evaluation after the public receipt. Existing output files are not overwritten unless `--overwrite` is passed.

### Policy Discovery

Policy context is optional. When `--policy` is not provided, the prototype looks for:

1. `AI_POLICY.md`
2. `CONTRIBUTING.md`

If neither file exists, generation continues and the receipt should say that no clear repository AI policy was available in the evaluated inputs.

### Current Scope

The prototype intentionally keeps v1 narrow:

- It treats transcripts as plain text.
- It fetches PR title, body, URL, and head SHA.
- It fetches linked issue title and body when `--issue` is provided.
- It does not fetch or evaluate the full diff.
- It does not post comments back to GitHub.
- It does not produce signed receipts or tamper-resistant provenance.
