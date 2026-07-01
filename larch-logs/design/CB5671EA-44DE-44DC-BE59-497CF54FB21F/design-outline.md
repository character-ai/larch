## Proposed Design Outline

### Goals
- Cut real prose tokens (not blank lines) in `skills/design/references/discussion-rounds.md` by roughly 15%, banked via the byte/token closure ratchet.
- Preserve every behavior-bearing literal: the Q&A output schema, the `discussion-round1.md` / `discussion-round2.md` filenames, the settle-dispatch two-line directive, and all step-anchor HTML comments.

### Non-goals
- No discussion-flow, cap, or short-circuit semantics changes.
- No changes to `SKILL.md`, `approval-gates.md`, or any other reference file.

### Approach sketch
- Line-by-line tightening of the front-matter (Consumer/Contract/When to load/Binding convention) and body prose (Step 1c questions guidance, Step 1d behavior/output/cap sections, post-plan Round 2 body), following the compression style already used in the sibling `approval-gates.md` pass (#5874/PR #5900).
- Merge redundant clauses and restated context; keep the two structural-pin lines (`settle-rc-dispatch.md` read directive + `SETTLE_NEXT_ACTION` line, pinned by `scripts/test-design-structure.sh`) byte-identical.
- Regenerate `python/skill-closure-baseline.json` via `python3 python/cli.py lint skill-closure-growth --write` to bank the reduction, the same mechanism the sibling PR used.

### Surfaces in scope
- `skills/design/references/discussion-rounds.md`
- `python/skill-closure-baseline.json`

### Open questions
- None.
