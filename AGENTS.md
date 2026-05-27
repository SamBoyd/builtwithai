# Software Development Principles

We follow strict YAGNI and KISS: choose the smallest change that satisfies the current requirement.

Do not add params, flags, fields, modules, abstractions, normalization, configurability, fallback paths, or future-facing behavior until the requirement being implemented needs them. Introduce each new knob only at the commit where a concrete caller or test exercises it.

# Project structure

- `docs/`: source project notes and proposal drafts.
- `site/`: Astro static site intended for Cloudflare Pages.
- `site/src/pages/`: route entrypoints, including the homepage and blog routes.
- `site/src/components/`: reusable Astro UI components.
- `site/src/layouts/`: shared page and blog post layouts.
- `site/src/content/blog/`: Markdown blog posts.
- `site/src/styles/`: global CSS and theme variables.

# Python prototype

Run prototype CLI modules from the repository root with `python3 -m prototype.cli ...`, not `python3 prototype/cli.py ...`. Prefer normal package imports such as `from prototype import transcript`; do not add script-mode fallback imports just to support direct file execution.

When adding Python dependencies to a requirements file, pin each dependency to the latest available version from `pip index versions <package>`.

# Summary additions


After completing a major code change, include a suggested git commit message at the end of your response.

Use Conventional Commits v1.0.0 structure:

`<type>[optional scope][!]: <description>`

`[optional body]`

`[optional footer(s)]`

Follow these rules:

- Use a valid type. Prefer: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `ci`, `build`, `perf`, `revert`.
- Add an optional scope when helpful (for example `sync`, `blog`, `mixpanel`, `content`, `docusaurus`).
- Keep the description short, specific, and actionable.
- Add a body when context is useful; separate it from the header with one blank line.
- IMPORTANT: Explain intent and impact in the body (why this change was needed, what behavior changed). 
- Use footers for metadata like issue refs (`Refs: #123`) or review trailers (`Reviewed-by: name`).
- Mark breaking changes with `!` in the header and/or a `BREAKING CHANGE: <description>` footer.
- Keep formatting machine-parseable and consistent so release tooling can use commit history.

Format the suggestion as:

**Suggested commit message:**
```text
<type>(<scope>): <short description>

<optional body explaining intent and impact>

<optional footer(s)>
```
