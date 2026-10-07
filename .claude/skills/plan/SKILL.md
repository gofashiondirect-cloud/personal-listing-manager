---
name: plan
description: Plan a change before building it, research the plan against the right sources, and track proof for every item. Use before any feature or change bigger than a one-line fix, and whenever the user asks to plan, design or "think it through first".
---

# Plan → research → prove

## 1. Size it
- **Tiny** (typo, colour, one-line fix): no plan. Just do it.
- **Normal** (one feature, a few files): short plan, only the sections that apply.
- **Big** (many files, new data, auth/payments, unclear request): full plan; show it to the user and wait for OK.
- **New app or major product feature**: first write a product requirements doc from `templates/PRD.md` to `.claude/plans/prd-<slug>.md` (problem, users, goals, MVP user stories with acceptance criteria, out of scope, UX, data/privacy, release slices). Agree it with the user, then plan each release slice.

## 2. Write the plan
Copy `.claude/kit/templates/PLAN.md` (or `~/.claude/templates/PLAN.md`) to `.claude/plans/current.md` and fill it in. Every item is a checkbox; leave out sections that don't apply instead of writing "N/A".

## 3. Research the plan, in this order (stop as soon as a source answers it)
1. **The request.** Every point the user asked for is an item; nothing extra. Unclear? Ask once.
2. **The project.** CLAUDE.md, `## Preferences`, the project map, the closest existing feature (follow its pattern), installed versions in package.json / requirements / lockfiles.
3. **Saved research.** `.claude/research/*.md` notes newer than ~90 days: reuse them.
4. **Official docs, live, for the installed versions** (react.dev, nextjs.org, docs.djangoproject.com, MDN, the library's changelog). Delegate to a subagent: "check X in the docs for version Y; reply in under 150 words with links".
5. **Standards.** `.claude/standards/architecture.md` (where code goes, layers, boundaries), `ux.md` for anything users see, `privacy.md` when personal data, cookies, analytics or payments are involved, `devops.md` for deploy/CI/hosting, and the checklist for each file type, plus WCAG 2.2 AA (accessibility), OWASP Top 10 (security), Core Web Vitals (speed), the language style guide.
Fix the plan with what you learn. Save anything reusable to `.claude/research/<topic>.md` (date, versions, findings, links; under 30 lines).

## 4. Build against the plan
Tick an item only with proof written after it: `- [x] item - proof: tests/test_cart.py::test_coupon passes` or `- proof: src/cart.ts:42`, `- proof: htmlcheck OK`, `- proof: visual diff reviewed, only header changed`. The Stop hook blocks finishing while any item is unticked or lacks proof. If an item turns out unnecessary, change it to `- [x] item - dropped: <reason>`.

## 5. Sign-off per discipline
The Stop hook works out which disciplines the changed files touch (Engineering per language, Architecture for new files, UX/UI, QA, Database, API, Privacy & security, DevOps) and requires one ticked line each under `## Sign-off`, e.g. `- [x] UX/UI: ux.md met - proof: empty state + error message added (index.html:40), visual diff reviewed`. Use `n/a: <reason>` only if the standard genuinely doesn't apply.

## 6. Final review (before commit)
- Re-read the user's request and the plan's "Done when"; confirm each point.
- Run the `code-review` skill on the diff (low effort for normal plans, medium for big ones) and fix real findings.
- Tick the `Review` item with what you checked; then set `Status: done`. Commits are blocked while a plan is open without a ticked review.
