from prototype.github_context import PullRequestContext
from prototype.transcript import Transcript


PROMPT_TEMPLATE = """You are generating a BuiltWithAi PR Ownership Receipt.

Purpose:
Evaluate whether the transcript shows human ownership of an AI-assisted pull request. AI involvement is expected. Do not decide whether AI wrote the code. Decide what human judgment is visible, what is missing, and what maintainer action is recommended.

No-evidence rule:
If the transcript does not show a kind of contributor ownership, do not credit that ownership merely because the PR description, issue response, or generated artifact looks coherent.

Use the provided transcript, PR context, issue context, and policy context only. Distinguish transcript evidence from PR/issue context. Passing tests are validation evidence, not ownership evidence, unless the transcript shows the contributor choosing, requesting, interpreting, or responding to them.

Keep the public receipt compact and maintainer-facing. Do not reveal private transcript details unnecessarily in the public receipt. Never claim policy compliance when no policy text was provided.

Return structured output matching the provided Pydantic schema:
- private_evaluation
- public_receipt

Public receipt fields:
- status
- policy_fit
- human_ownership
- ai_role
- evidence_reviewed
- tests_checks_run
- reviewer_attention_requested
- known_risks_or_unknowns
- recommended_next_step
- receipt_binding

Ownership rubric questions:
1. Did the contributor understand the issue before implementation?
2. Did they ask clarifying questions or challenge assumptions?
3. Did they evaluate alternative solutions?
4. Did they approve or modify the plan for reasons they could explain?
5. Did they make tradeoff judgments?
6. Did they notice missing tests, edge cases, or refactor opportunities?
7. Did they steer the work rather than merely accept generated output?
8. Did they review the final change in relation to the original issue?
9. Did the transcript expose remaining risks or unknowns?

Evidence levels:
- visible: the transcript directly shows the contributor doing the relevant ownership work.
- weak: the transcript hints at ownership, but the evidence is shallow, generic, or mostly supplied by the agent.
- missing: the available inputs do not show the ownership dimension.
- contradictory: the transcript suggests the contributor did not own the work in the relevant way.

Transcript path: {transcript_path}
Transcript mode: {transcript_mode}
Transcript:
{transcript_content}

PR context:
PR number: {pr_number}
PR title: {pr_title}
PR body: {pr_body}
PR URL: {pr_url}
PR head SHA: {pr_head_sha}

Issue context: no issue context provided

Policy context: no policy found
"""


def build_receipt_prompt(loaded_transcript: Transcript, pr_context: PullRequestContext) -> str:
    return PROMPT_TEMPLATE.format(
        transcript_path=loaded_transcript.path,
        transcript_mode=loaded_transcript.mode,
        transcript_content=loaded_transcript.content,
        pr_number=pr_context.number,
        pr_title=pr_context.title,
        pr_body=pr_context.body,
        pr_url=pr_context.url,
        pr_head_sha=pr_context.head_sha,
    )
