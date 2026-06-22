## Proposed Design Outline

### Goals
- Add a generic, hand-maintained `ARCHITECTURAL_GUIDELINES.md` at the operating repo's root; when present, `/design` and `/implement` consult it as aspirational goals and surface deviations.
- Ship larch's own seeded copy (the issue's seed set) as the first consumer; link it from `AGENTS.md` canonical sources.
- Absent file means exact same behavior as today, covered by a test.

### Non-goals
- Neither skill ever auto-edits the file; it stays hand-maintained.
- No companion audits/lints (#5000, #5001, #5002, #5003, #4997) and no future categories (Contracts, Observability, Testing).
- No mechanical enforcement; entries are non-deterministic by definition.

### Approach sketch
- Create `ARCHITECTURAL_GUIDELINES.md` (root) with the issue's seed set under the `### G-<area>-<n>: goal / Why / Deviate when` schema.
- `/design`: load lazily alongside Design Mindset; list deviations plus rationale at proposal-approval (Step 1d.7 outline gate) and final-plan-approval (Gate C). Emit a brief "consulted; no deviations" note when clean.
- `/implement`: load and warn on deviations into the PR body plus run summary; no blocking gate; emit the same clean-run note.
- Discover at git toplevel or `CLAUDE_PROJECT_DIR`; absent means no-op in both skills.
- Add a test asserting the absent-file no-op invariant.

### Surfaces in scope
- New `ARCHITECTURAL_GUIDELINES.md` (root); `AGENTS.md` canonical-sources link.
- `skills/design/SKILL.md` and `skills/implement/SKILL.md`, plus lazy-loaded `references/` content per G-Skill-1.
- A discovery/load helper and its test under `python/` per G-Skill-2.

### Open questions
- Discovery/loading: thin `python/cli.py` verb (logic-in-Python, G-Skill-2) versus prompt-only Read. Leaning Python; finalized at plan drafting and review.
