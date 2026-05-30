from prototype.github_context import IssueContext, PullRequestContext
from prototype.policy import PolicyContext
from prototype.transcript import Transcript


PROMPT_TEMPLATE = """You are generating a BuiltWithAi PR Ownership Receipt.

Purpose:
Evaluate whether the transcript shows human ownership of an AI-assisted pull request. AI involvement is expected. Do not decide whether AI wrote the code. Decide what human judgment is visible, what is missing, and what maintainer action is recommended.

No-evidence rule:
If the transcript does not show a kind of contributor ownership, do not credit that ownership merely because the PR description, issue response, or generated artifact looks coherent.

Use the provided transcript, PR context, issue context, and policy context only. Distinguish transcript evidence from PR/issue context. Passing tests are validation evidence, not ownership evidence, unless the transcript shows the contributor choosing, requesting, interpreting, or responding to them.

Keep the public receipt compact and maintainer-facing. Do not reveal private transcript details unnecessarily in the public receipt. Never claim policy compliance when no policy text was provided. If policy status is none_found, policy_fit must say that no clear repository AI policy was available in the evaluated inputs.

Return structured output matching the provided Pydantic schema:
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

{pr_context}

{issue_context}

{policy_context}
"""


def format_pr_context(pr_context: PullRequestContext) -> str:
    return (
        "PR context:\n"
        f"PR number: {pr_context.number}\n"
        f"PR title: {pr_context.title}\n"
        f"PR body: {pr_context.body}\n"
        f"PR URL: {pr_context.url}\n"
        f"PR head SHA: {pr_context.head_sha}"
    )


def format_issue_context(issue_context: IssueContext | None) -> str:
    if issue_context is None:
        return "Issue context: no issue context provided"
    return (
        "Issue context:\n"
        f"Issue number: {issue_context.number}\n"
        f"Issue title: {issue_context.title}\n"
        f"Issue body: {issue_context.body}"
    )


def format_policy_context(policy_context: PolicyContext | None) -> str:
    if policy_context is None or policy_context.status == "none_found":
        return "Policy context: no policy found"
    return (
        "Policy context:\n"
        f"Policy status: {policy_context.status}\n"
        f"Policy path: {policy_context.path}\n"
        f"Policy text:\n{policy_context.content}"
    )


def build_receipt_prompt(
    loaded_transcript: Transcript,
    pr_context: PullRequestContext,
    issue_context: IssueContext | None = None,
    *,
    policy_context: PolicyContext | None = None,
) -> str:
    return PROMPT_TEMPLATE.format(
        transcript_path=loaded_transcript.path,
        transcript_mode=loaded_transcript.mode,
        transcript_content=loaded_transcript.content,

        pr_context=format_pr_context(pr_context),
        issue_context=format_issue_context(issue_context),
        policy_context=format_policy_context(policy_context),
    )
