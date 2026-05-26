---
type: resource
status: draft
owner: shared
updated: 2026-05-26
created: 2026-05-26
confidence: low
---

# BuiltWithAi - transcript-supported PR spec

This is a self-contained implementation spec for a separate-project prototype. It should be possible to copy this file into another repository and build the CLI without access to the original Obsidian vault.

## Background

BuiltWithAi is a proposed trust layer for AI-assisted work. The core claim is not "no AI was used." The claim is:

> This was built with AI, but the major judgments were made by a human who reviewed, shaped, and stands behind the work.

The immediate prototype target is open-source pull requests. The problem is that a polished PR no longer reliably signals effort, understanding, or follow-through, because AI can cheaply generate plausible code, tests, docs, and PR descriptions. Maintainers still carry the expensive work of deciding whether the contribution is correct, useful, safe, and worth reviewing.

This prototype explores whether a full AI-assisted development transcript can make contributor judgment visible enough to generate a useful maintainer-facing receipt.

The receipt is not a proof of correctness. It is a compact review aid that says what human ownership is visible, what AI appears to have done, what evidence was reviewed, what is missing, and what the maintainer should do next.

## Prototype Goal

Build a local Python CLI that:

1. Reads an AI-assisted development transcript.
2. Fetches GitHub PR context using PyGithub.
3. Fetches linked issue context when provided or inferable.
4. Reads an optional repository AI or contribution policy.
5. Sends the assembled context to an OpenAI model using Pydantic structured output through Instructor.
6. Produces:
   - a private heuristic evaluation for debugging and prompt iteration;
   - a public BuiltWithAi PR Ownership Receipt suitable for a PR comment.

The generator should answer:

> Given a transcript, PR context, linked issue context, and optional repository policy text, can an LLM generate a compact public receipt that makes visible human ownership and missing evidence legible to a maintainer?

## Key Principle

The evaluator must follow a no-evidence rule:

> If the transcript does not show a kind of contributor ownership, do not credit that ownership merely because the PR description, issue response, or generated artifact looks coherent.

The transcript is the main evidence of human judgment. The PR and issue provide context, artifact binding, and validation claims, but a polished final artifact is not proof that the contributor understood or owned the change.

## Non-Goals

- Do not build this prototype inside the Obsidian vault.
- Do not compare generated receipts to hand-written expected receipts.
- Do not build an eval harness in v1.
- Do not build CI integration or a GitHub app.
- Do not require full final diff review.
- Do not implement signed receipts, tamper resistance, transcript provenance, anti-gaming, or audit trails.
- Do not claim to prove contributor sincerity, code correctness, or absence of AI-generated code.
- Do not expose the full transcript publicly by default.

## CLI Shape

Working command name:

```bash
builtwithai-receipt TRANSCRIPT_PATH --pr 3 --issue 1
```

The CLI should use Python and `click`.

### Required Arguments

- `TRANSCRIPT_PATH`: path to the full AI-assisted development transcript.
- `--pr`: PR number or GitHub PR URL.

The command is expected to be run from inside the local git repository where the PR was opened. The local repo is used to identify the GitHub repository and to discover policy files.

### Optional Arguments

- `--issue`: issue number or GitHub issue URL
- `--policy`: explicit path to a repository AI or contribution policy file.
- `--model`: OpenAI model name. Default should be configurable in code; a strong first default is `gpt-5.5`, with cheaper model experimentation allowed by CLI override.
- `--receipt-output`: write the public receipt markdown to this file instead of stdout.
- `--private-eval-output`: write the private heuristic evaluation JSON or markdown to this file.
- `--show-private-eval`: print the private heuristic evaluation to stdout as well as the public receipt.
- `--repo`: optional `owner/name` override when local git remote detection is ambiguous.
- `--github-token-env`: environment variable name for the GitHub token. Default: `GITHUB_TOKEN`.
- `--openai-api-key-env`: environment variable name for the OpenAI API key. Default: `OPENAI_API_KEY`.
- `--overwrite`: allow overwriting existing output files.

### Output Defaults

- If `--receipt-output` is not provided, print the public receipt to stdout.
- Do not print the private heuristic evaluation unless `--show-private-eval` is set.
- If both receipt and private evaluation are printed to stdout, separate them with clear headings.
- If output files already exist, fail unless `--overwrite` is provided.

## Argument Validation

The CLI should fail early with actionable errors when:

- `TRANSCRIPT_PATH` does not exist or is not readable.
- `--pr` cannot be parsed as a PR number or GitHub PR URL.
- `--issue` is provided but cannot be parsed as an issue number or GitHub issue URL.
- The command is not run inside a git repository and `--repo` is not provided.
- The repository owner/name cannot be inferred from local git remotes and `--repo` is not provided.
- `--policy` is provided but the file does not exist or is not readable.
- `--receipt-output` or `--private-eval-output` points to an existing file without `--overwrite`.
- The OpenAI API key is missing.
- GitHub context cannot be fetched with the available token or unauthenticated access.

Missing issue context and missing policy context should not be fatal. They should be represented in the model input and surfaced in the receipt as missing context.

## Policy Discovery

Policy discovery order:

1. If `--policy` is provided, use that file.
2. Otherwise, look for `AI_POLICY.md` at the repository root.
3. If not found, look for `CONTRIBUTING.md` at the repository root.
4. If neither exists, continue with `policy_status = "none_found"`.

The prototype should not search the entire repository for policy-like text in v1. Keep policy discovery predictable.

The policy file should be passed to the LLM as context. The LLM should not be asked to infer policy from unrelated repository files.

When no policy text is available, the receipt must not claim policy compliance. It should say that no clear repository AI policy was available in the evaluated inputs.

## GitHub Context Collection

Use `PyGithub` rather than shelling out to the `gh` CLI.

PyGithub can access the GitHub REST API from Python and supports token authentication. As of 2026-05-26, PyPI lists `PyGithub` `2.9.1`, released 2026-04-14, requiring Python `>=3.9`.

### Authentication

- Read the GitHub token from `GITHUB_TOKEN` by default.
- If no token is present, allow unauthenticated access for public repositories only if PyGithub supports the requested calls without authentication.
- If unauthenticated access fails, report that a GitHub token is required.

### GitHub Token Permissions

The prototype only needs read access to repository metadata, pull requests, issues, commits, and file contents for policy discovery.

For a fine-grained GitHub personal access token, use the narrowest practical scope:

- Repository access: only the target repository, when possible.
- Contents: read-only. Needed to read `AI_POLICY.md` or `CONTRIBUTING.md` from the repository when policy discovery reads through the GitHub API in a future version. The v1 local-file discovery path can work without this if the policy file is read from disk.
- Pull requests: read-only. Needed to fetch PR title, body, state, head SHA, changed files, and commit metadata.
- Issues: read-only. Needed to fetch linked issue title, body, state, labels, and author.
- Metadata: read-only. This is required by GitHub for fine-grained tokens and is enough for basic repository metadata.

For public repositories, the CLI may work without a token or with only unauthenticated API access, but rate limits will be lower and private repositories will fail.

For classic personal access tokens, prefer `repo:status`-style narrow permissions only if they satisfy PyGithub's calls. If using a private repository and a classic token is unavoidable, `repo` may be required, but the implementation should document that fine-grained read-only repository access is preferred.

The token must never need write permissions for v1. It should not be able to create comments, open PRs, update issues, push code, administer repositories, read secrets, or manage workflows.

### Repository Resolution

Resolve the GitHub repository from:

1. `--repo owner/name`, when provided.
2. Local git remote URL, preferring `origin`.

Support common remote URL shapes:

- `git@github.com:OWNER/REPO.git`
- `https://github.com/OWNER/REPO.git`
- `https://github.com/OWNER/REPO`

For v1, GitHub Enterprise URLs are out of scope unless `--repo` and a future `--github-base-url` are added.

### PR Input

Fetch PR context:

- PR number
- PR title
- PR body

Do not fetch or include the full diff in v1. The prototype is intentionally testing whether transcript-visible judgment can be evaluated without full patch review.

### Issue Input

If `--issue` is provided, fetch:

- issue number
- issue title
- issue body

## Transcript Input

The transcript input can initially be treated as plain text.

The CLI should not assume every transcript is clean JSONL, even though some fixtures may be exported Codex session logs. It should preserve enough content for the LLM to distinguish:

- user messages;
- agent messages;
- tool calls and results when present;
- test or verification output when present;
- branch, commit, push, and PR creation events when present.

For v1, support these transcript modes:

- `auto`
- `text`
- `codex-jsonl`

`auto` should default to text if parsing fails.

Codex JSONL parsing, if implemented, should extract a readable transcript summary preserving user turns, assistant turns, tool calls, and tool outputs. It should not include system or developer instructions unless they are directly relevant to the work product.

## LLM Client

Use the OpenAI API from Python.

Use `instructor` with Pydantic models to request structured output from the LLM. As of 2026-05-26, PyPI lists `instructor` `1.15.1`, released 2026-04-03, requiring Python `>=3.9`.

OpenAI Structured Outputs should be treated as the underlying reliability goal: prefer schema-constrained responses over free-form JSON. The implementation may use Instructor's OpenAI integration for validation and retries, but the public application interface should be normal Pydantic models.

Environment:

- `OPENAI_API_KEY` is required by default.
- The model is chosen with `--model`.
- Temperature should default low for repeatability.
- The request should include enough max output budget for both private evaluation and public receipt.

## Conceptual Model

The evaluator should distinguish:

- transcript evidence: visible contributor thinking, steering, questions, choices, review, and follow-up;
- PR context: final title, description, files, commits, head SHA, test claims, and artifact binding;
- issue context: the work request and problem statement;
- policy context: project rules for AI-generated or AI-assisted work;
- missing evidence: ownership dimensions that are not visible in the transcript;
- polished output: coherent PR text or code that may have been generated by the agent and should not be treated as ownership evidence by itself.

The core question is not "did AI write the code?" In this workflow, AI-written code is expected. The core question is:

> Does the transcript show that a human understood, steered, reviewed, and accepted responsibility for the change enough that a maintainer should spend review attention on it?

## Evidence Levels

Use these internal evidence levels in the private heuristic evaluation:

### Visible Evidence

The transcript directly shows the contributor doing the relevant ownership work.

Examples:

- the contributor restates the issue in their own words;
- the contributor asks a question that changes the implementation path;
- the contributor rejects a broader or riskier agent plan;
- the contributor chooses between alternatives for a stated reason;
- the contributor requests a specific test, refactor, or edge-case check;
- the contributor identifies a remaining uncertainty and asks the reviewer to focus there.

### Weak Evidence

The transcript hints at ownership, but the evidence is shallow, generic, or mostly supplied by the agent.

Examples:

- the contributor approves a plan but gives no reason;
- the contributor asks for tests only after the agent suggests them;
- the contributor says they reviewed the diff, but the transcript shows no details of what they checked;
- the contributor repeats the issue text without adding understanding or judgment.

### Missing Evidence

The available inputs do not show the ownership dimension.

Missing evidence is not automatic failure. It means the evaluator should not give credit for that dimension.

Examples:

- no visible final review against the issue;
- no visible alternative considered;
- no visible tradeoff reasoning;
- no visible contributor response to risk or uncertainty.

### Contradictory Evidence

The transcript suggests the contributor did not own the work in the relevant way.

Examples:

- the contributor asks the agent to handle maintainer review questions for them;
- the contributor submits a PR after the agent or policy context says the project does not accept this kind of AI-generated patch;
- the contributor approves a change while admitting they do not understand the affected code path;
- the contributor ignores a risk or failing check raised by the agent.

## Ownership Rubric

The private heuristic evaluation should answer each ownership question in prose. It should identify the strongest visible evidence, name important missing evidence, avoid inferring understanding from final output quality, and explain how much confidence the evidence supports.

Rubric questions:

1. Did the contributor understand the issue before implementation?
2. Did they ask clarifying questions or challenge assumptions?
3. Did they evaluate alternative solutions?
4. Did they approve or modify the plan for reasons they could explain?
5. Did they make tradeoff judgments?
6. Did they notice missing tests, edge cases, or refactor opportunities?
7. Did they steer the work rather than merely accept generated output?
8. Did they review the final change in relation to the original issue?
9. Did the transcript expose remaining risks or unknowns?

Guidance for each question:

- Issue understanding: look for the contributor using their own words, distinguishing expected from actual behavior, or connecting the issue to specific code paths, user impact, or project constraints. Do not credit understanding merely because the agent explains the issue well.
- Clarifying questions or challenges: look for questions that change the plan, narrow scope, reveal ambiguity, or test whether the agent's interpretation is too broad.
- Alternatives: look for visible comparison between approaches, even informal comparison.
- Plan approval or modification: look for stated reasons, constraints, or acceptance criteria. Approval without reasons is weak evidence.
- Tradeoffs: look for decisions around scope, compatibility, risk, maintainability, test coverage, performance, or submission type.
- Tests, edge cases, refactors: look for the contributor identifying gaps, not only the agent proposing quality improvements.
- Steering: look for interventions that change direction, reject work, narrow scope, request cleanup, or pause implementation until the problem is clearer.
- Final review: look for the contributor comparing the final PR description, agent summary, or diff summary back to the issue. If full final diff review is not visible, surface that gap.
- Risks or unknowns: look for uncertainties preserved into the PR description or reviewer-attention request.

## Structured Output Model

The LLM should return one top-level object containing:

- `private_evaluation`
- `public_receipt`

### Private Heuristic Evaluation

The private evaluation is not meant for maintainers by default. It should be useful for debugging the prototype and improving the prompt.

Fields:

- `summary`: brief overall judgment.
- `inputs_reviewed`: list of evidence sources actually used.
- `missing_inputs`: list of unavailable but relevant inputs.
- `policy_assessment`: prose assessment of policy context.
- `ownership_questions`: list of question evaluations.
- `evidence_gaps`: maintainer-relevant missing evidence.
- `risk_notes`: risks, limits, and unknowns.
- `receipt_rationale`: why the public receipt status and recommendation were chosen.

Each ownership question evaluation should include:

- `question`: the rubric question.
- `evidence_level`: one of `visible`, `weak`, `missing`, `contradictory`.
- `evidence`: concise prose describing transcript support.
- `missing_evidence`: concise prose describing what was not shown.

Do not include hidden chain-of-thought. The private evaluation should be structured explanatory prose, not raw model reasoning.

### Public Receipt

The public receipt should contain these fields:

- `status`
- `policy_fit`
- `human_ownership`
- `ai_role`
- `evidence_reviewed`
- `tests_checks_run`
- `reviewer_attention_requested`
- `known_risks_or_unknowns`
- `recommended_next_step`
- `receipt_binding`

Allowed status values:

- `Reviewable`
- `Caution`
- `Not recommended as PR`

Choose the receipt status from the whole evaluation, not just one ownership question:

- `Reviewable`: visible ownership, no obvious policy conflict, and only ordinary reviewable gaps.
- `Caution`: partial ownership evidence, important missing evidence, unclear policy fit, or weak final-review signal.
- `Not recommended as PR`: policy conflict, contradictory ownership evidence, no meaningful human steering, or evidence that the work should be an issue, reproduction, specification, or change plan instead.

## Public Receipt Markdown Format

Render the public receipt as markdown from structured fields:

```md
BuiltWithAi PR Ownership Receipt

Status: Reviewable / Caution / Not recommended as PR

Policy fit: ...

Human ownership: ...

AI role: ...

Evidence reviewed: ...

Tests/checks run: ...

Reviewer attention requested: ...

Known risks or unknowns: ...

Recommended next step: ...

Receipt binding: ...
```

The structured model should store these fields separately, then render markdown from the structured object. Do not ask the model to hand-format the only copy of the receipt.

The public receipt should be compact enough to paste into a PR comment.

## Receipt Field Guidance

- `Status`: maintainer-facing review-readiness recommendation.
- `Policy fit`: how the PR appears to fit the receiving repository's AI policy or contribution rules. If no policy was found, say that policy compliance cannot be claimed.
- `Human ownership`: what level and kind of human understanding, judgment, review, and answerability is visible in the transcript.
- `AI role`: how AI was used, such as planning, code generation, debugging, test writing, documentation, copy-editing, review, branch operations, or PR creation.
- `Evidence reviewed`: transcript, PR metadata, issue context, policy text, changed file list, commit metadata, and any missing inputs that matter.
- `Tests/checks run`: validation work visible in the transcript or PR body. Do not treat passing tests as direct ownership evidence unless the contributor chose, requested, interpreted, or responded to them.
- `Reviewer attention requested`: specific assumptions, risks, design choices, or missing evidence a maintainer should focus on.
- `Known risks or unknowns`: policy uncertainty, missing final review, missing issue context, no visible risk analysis, or any explicit limitations.
- `Recommended next step`: review, review with caution, ask for more ownership evidence, request specific checks, convert to issue/specification/change plan, or avoid submitting/reviewing as a PR.
- `Receipt binding`: PR number, PR URL, head SHA, issue number or URL, policy status or policy file, and generation timestamp if available.

## Prompt Requirements

The system or developer prompt should tell the model:

- You are evaluating whether human ownership is visible in the transcript.
- The question is not whether AI wrote code; AI involvement is expected.
- Do not infer ownership from the final PR looking polished.
- Treat tests/checks as validation evidence, not ownership evidence, unless the transcript shows the contributor choosing, requesting, interpreting, or responding to them.
- Surface missing evidence plainly.
- Keep the public receipt compact and maintainer-facing.
- Make the recommended next step more important than any score-like judgment.
- Never claim policy compliance when no policy text was provided.
- Do not reveal private transcript details unnecessarily in the public receipt.
- Distinguish evidence visible in the transcript from context visible in the PR or issue.
- Preserve policy conflicts even when human ownership is strong.

## Suggested Prompt Skeleton

Use this as a starting point for the LLM call:

```text
You are generating a BuiltWithAi PR Ownership Receipt.

Purpose:
Evaluate whether the transcript shows human ownership of an AI-assisted pull request. AI involvement is expected. Do not decide whether AI wrote the code. Decide what human judgment is visible, what is missing, and what maintainer action is recommended.

No-evidence rule:
If the transcript does not show a kind of contributor ownership, do not credit that ownership merely because the PR description, issue response, or generated artifact looks coherent.

Use the provided transcript, PR context, issue context, and policy context only. Distinguish transcript evidence from PR/issue context. Passing tests are validation evidence, not ownership evidence, unless the transcript shows the contributor choosing, requesting, interpreting, or responding to them.

Return structured output matching the provided Pydantic schema:
- private_evaluation
- public_receipt
```

Then include:

- transcript text;
- PR context;
- issue context or explicit "no issue context provided";
- policy text or explicit "no policy found";
- rubric questions and evidence-level definitions.

## Rendering Rules

The CLI should render:

1. public receipt markdown;
2. optional private evaluation markdown or JSON.

Public receipt markdown should be concise enough to paste into a PR comment.

Private evaluation output can be more verbose and should preserve the evidence-level structure for debugging.

## Error Handling

Expected failure modes:

- invalid CLI arguments;
- missing local git repository;
- unparseable GitHub remote;
- missing GitHub token for private repo;
- PR or issue not found;
- API rate limit or network failure;
- unreadable transcript or policy file;
- LLM schema validation failure;
- output file already exists.

All errors should be printed in plain language. Include the failing input where useful, but avoid printing secrets.

## Suggested Package Shape

Possible Python package modules:

- `builtwithai_receipt/cli.py`: Click command definitions and argument validation.
- `builtwithai_receipt/controller.py`: control flow for generating the receipt.
- `builtwithai_receipt/github_context.py`: PyGithub client and PR/issue fetching.
- `builtwithai_receipt/git_repo.py`: local repo and remote parsing.
- `builtwithai_receipt/policy.py`: policy discovery and loading.
- `builtwithai_receipt/transcript.py`: transcript loading and optional parsing.
- `builtwithai_receipt/schemas.py`: Pydantic models.
- `builtwithai_receipt/prompt.py`: prompt template assembly.
- `builtwithai_receipt/llm.py`: OpenAI and Instructor client wrapper.
- `builtwithai_receipt/render.py`: markdown rendering for receipt and private evaluation.

## Suggested Dependencies

Runtime:

- `click`
- `openai`
- `instructor`
- `pydantic`
- `PyGithub`

Development:

- `pytest`
- `pytest-mock`
- `ruff` or equivalent formatter/linter if desired

Version pins can be chosen in the implementation project. Current reference versions checked while writing this spec:

- `PyGithub` `2.9.1` on PyPI, released 2026-04-14.
- `instructor` `1.15.1` on PyPI, released 2026-04-03.

## Acceptance Criteria

The prototype is acceptable when:

- It can be run from inside a GitHub-backed repo with a transcript path and PR number.
- It fetches PR context through PyGithub, not the `gh` CLI.
- It fetches issue context when an issue is provided or can be inferred.
- It discovers `AI_POLICY.md`, then `CONTRIBUTING.md`, when no explicit policy path is provided.
- It continues when no policy file exists and reflects that uncertainty in the receipt.
- It calls the OpenAI API with a selectable model.
- It uses Pydantic structured output through Instructor.
- It renders a public receipt with the required fields.
- It can optionally emit the private heuristic evaluation.
- It does not compare output to hand-written expected receipts.
- It does not require access to any Obsidian vault notes.

## First Manual Test Cases

Use two manually prepared transcript fixtures:

1. A shallow/passive transcript where the contributor gives one broad instruction such as "pull issue #1, implement it, and submit a PR," while the agent reads the issue, chooses the implementation shape, writes code and tests, fixes failures, writes the PR, pushes, and opens the PR with no visible human steering.
2. A strong-ownership transcript where the contributor defines the implementation contract before coding, chooses Python version and libraries, specifies CLI behavior, asks for tests, requests branch hygiene, directs a refactor, notices missing argument-validation tests, reviews the PR description, and asks for an "Example usage" section before PR creation.

Example public GitHub artifacts from the original prototype:

- Shallow/passive fixture: PR `https://github.com/SamBoyd/toy-fizzbuzz/pull/2`, issue `https://github.com/SamBoyd/toy-fizzbuzz/issues/1`.
- Strong-ownership fixture: PR `https://github.com/SamBoyd/toy-fizzbuzz/pull/3`, issue `https://github.com/SamBoyd/toy-fizzbuzz/issues/1`.

For each run, manually inspect whether:

- shallow/passive ownership is not over-credited;
- strong ownership is recognized without ignoring policy uncertainty;
- missing final diff review is surfaced rather than invented;
- tests/checks are described as validation evidence, not automatic ownership evidence;
- receipt binding includes PR number, head SHA, issue number, and policy status.

## Example Receipt Behavior

For a shallow/passive transcript:

- Under a policy allowing AI assistance only with human ownership, status should usually be `Not recommended as PR`.
- Under no clear AI policy, status should usually be `Caution`.
- Human ownership should say that only initial delegation is visible and that the transcript does not show diagnosis, planning, tradeoff judgment, test selection, final review, or answerability.

For a strong-ownership transcript:

- Under a policy allowing AI assistance with human ownership, status should usually be `Reviewable`.
- Under no clear AI policy, status should usually be `Caution`, because policy compliance cannot be claimed.
- Human ownership should mention visible steering and judgment, but still surface missing final line-by-line diff review if it is not shown.

For a policy that rejects AI-generated PRs:

- Status should be `Not recommended as PR` even if human ownership is strong.
- Recommended next step should suggest converting useful work into an issue comment, reproduction, specification, or change plan rather than submitting/reviewing the PR.

## Open Questions

- Should policy scenarios such as "no AI-generated PRs accepted" be supported as explicit fixture inputs, or should v1 only accept actual policy files?
- Should the CLI support GitHub Enterprise via `--github-base-url` in v1?
- Should private evaluation output default to JSON, markdown, or both?
- Should transcript adapters be added before prompt iteration, or is raw text enough for the first prototype?
- Should the CLI include `--include-diff` later as an opt-in stronger evidence mode?

## Implementation References

- PyGithub on PyPI: https://pypi.org/project/PyGithub/
- Instructor on PyPI: https://pypi.org/project/instructor/
- OpenAI Structured Outputs: https://developers.openai.com/api/docs/guides/structured-outputs
- OpenAI Responses API: https://platform.openai.com/docs/api-reference/responses

## Source Context

This spec was written on 2026-05-26 as part of the BuiltWithAi transcript-supported PR ownership receipt prototype. It intentionally contains the necessary context inline so it can be used outside the original note vault.
