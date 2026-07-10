## Proposed Design Outline

### Goals
- Reduce main-agent context residency by 10-17K tokens for typical /design runs by splitting large reference files so only executed gate slices load into context.
- Ensure Gate A content (`approval-gates-gate-a.md`) never enters context on the common path (no re-entry from Gate B(c)/Gate C(b)).
- Ensure `finalize-step5` failure-reporting content only loads when a failure path fires.

### Non-goals
- No behavioral change: gate semantics, AskUserQuestion prompts, loop routing, and apply logic stay byte-identical.
- No slimming of `discussion-rounds.md` or `design-outline.md` (already just-in-time; content unchanged).
- No Python changes: `python/plan_review.py`, `design_lifecycle.py`, etc. stay untouched.
- No change to gate trigger conditions or acceptance criteria.

### Approach sketch
- Split `approval-gates.md` into 4 files: a small shared core (review-round cap, renderer contract, severity rubric, shared post-apply pipeline, state invariants) plus `approval-gates-gate-a.md`, `approval-gates-gate-b.md`, and `approval-gates-gate-c.md`. Update SKILL.md Step 1e, Step 3.5, and Step 4b load directives to load shared core + the relevant gate slice only.
- Slim `plan-review.md`: extract the orchestration steps the main agent executes at Step 3 (MAV instructions, dedup rules, artifact templates, vote format, tiered panels) into `plan-review-runtime.md`; demote the authority/Python-internal content to `plan-review.md` (renamed to load-only-when-editing). Update SKILL.md Step 3 directive.
- Split `finalize-step5.md`: keep the green-path body (Step 5b OOS, 5b.5 diagram, 5c compose/publish, 5d warning replay) in the main file; extract `## /design auto error reporting` teardown into `finalize-step5-failures.md`. Update SKILL.md Step 5 to load the failure slice only on failure paths.
- Update all cross-file `approval-gates.md` section citations in SKILL.md, other references (`plan-review.md`, `finalize-step5.md`), and agent-lint S030 references.
- Regenerate `python/skill-closure-baseline.json` to reflect the new reference set.

### Surfaces in scope
- `skills/design/references/approval-gates.md` (split into 4)
- `skills/design/references/plan-review.md` (slim runtime content)
- `skills/design/references/finalize-step5.md` (split into 2)
- `skills/design/SKILL.md` (update 5–6 MANDATORY READ load directives + cross-file anchor citations)
- `python/skill-closure-baseline.json` (regenerate)
- New files: `approval-gates-gate-a.md`, `approval-gates-gate-b.md`, `approval-gates-gate-c.md`, `plan-review-runtime.md`, `finalize-step5-failures.md`

### Open questions
- None.
