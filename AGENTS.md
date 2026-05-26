# Software Development Principles

We follow strict YAGNI and KISS: choose the smallest change that satisfies the current requirement, and avoid adding fields, modules, normalization, overrides, or future-facing behavior until a concrete caller needs it.

# Project structure

- `docs/`: source project notes and proposal drafts.
- `site/`: Astro static site intended for Cloudflare Pages.
- `site/src/pages/`: route entrypoints, including the homepage and blog routes.
- `site/src/components/`: reusable Astro UI components.
- `site/src/layouts/`: shared page and blog post layouts.
- `site/src/content/blog/`: Markdown blog posts.
- `site/src/styles/`: global CSS and theme variables.

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
