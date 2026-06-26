## Proposed Design Outline

### Goals
- Eliminate OOS findings from the voter ballot entirely (pre-vote scope gate, option b).
- Lower per-reviewer OOS proposal volume from 3 to 1 (strengthen option a cap already in code).
- Keep `oos.md` as a session audit trail for operator-driven `/issue` follow-up.

### Non-goals
- Auto-filing OOS items via `oos-accepted-review.md` (voting eliminated, file stays empty).
- Plan review OOS behavior (`plan_review_round.py` cap unchanged; out of scope per issue surfaces).
- Changes to `oos-acceptance-rubric.md` (rubric remains valid at reviewer proposal time).
- Backwards-compatible OOS issue-filing: automatic OOS filing stops; manual follow-up via `oos.md`.

### Approach sketch
- One-line cap change: `PER_REVIEWER_OOS_PROPOSAL_CAP = 3 → 1` in `review_pipeline.py`.
- New `_apply_scope_gate(findings_file)` in `review_pipeline.py`: strip `[OUT_OF_SCOPE]` blocks from `findings.md` after `prune_nit_findings`, before voter dispatch; route to `_zero_findings_branch` when all findings stripped.
- Update `oos_proposal_instruction()` in `rendering.py` to say "at most 1"; regenerate generated agent files via `python3 python/cli.py generate ...`.
- Update 6 hand-maintained `agents/*.md` and `skills/shared/reviewer-templates.md` (one-line change each).
- Update 2 test files: `test_review_pipeline.py` (update cap test + add scope-gate test) and `test_rendering.py` (update cap string assertion).

### Surfaces in scope
- `python/review_pipeline.py`
- `python/rendering.py`
- `skills/shared/reviewer-templates.md`
- `agents/reviewer-{security,structure,edge-cases,plan-fidelity,correctness,testing}.md` (hand-maintained)
- `agents/code-reviewer.md`, `agents/reviewer-{code-robustness,security-structure-tests}.md`, `agents/pre-rendered/*.txt` (generated)
- `python/test_review_pipeline.py`, `python/test_rendering.py`

### Open questions
- None.
