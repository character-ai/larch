# Review Round 2

- Mode: `diff`
- 2 accepted, 1 rejected (0 neutral)

## Accepted Findings

### FINDING_3: Tool-absent excuse treats non-empty surviving outputs as success without collector OK
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: blocking
- **Concern**: In `python/larch/review/review_core_body.py`, the tool-absent excuse still treats non-empty surviving outputs as success via `review_threshold.py`, not just collector OK/cap_hit rows. When one vendor is absent and the survivor writes a non-empty but collector-rejected or non-substantive file, `_static_coverage_reason()` can return empty and the panel passes with no successful reviewer for that archetype.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Base the excuse on collector success for the surviving slot, or require collector OK/cap_hit before removing the absent vendor from missing


### FINDING_5: Stale reviewer-fallback documentation contradicts shipped --no-fallback dispatch
- **Reviewer(s)**: codex-generalist, dyn-dyn-review-loop-routing
- **Severity**: important
- **Concern**: Multiple docs still describe Cursor → Codex → Claude reviewer fallback and always-on panel output, while runtime reviewer panels now dispatch with `--no-fallback` and drop missing vendor rows. Stale prose appears in `skills/design/references/plan-review.md:98`, `docs/workflow-lifecycle.md:104`, and `docs/agents.md:49`, causing cross-doc routing guidance inconsistent with `skills/design/SKILL.md`, `docs/review-agents.md`, and `python/larch/review/plan_review_panel.py`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generalist: **Suggested fix:** Remove or rewrite the stale fallback prose so `/design`, `/review`, and `/implement` reviewer panels are consistently documented as vendor rows that drop without cross-vendor or Claude reviewer backfill.
  - From dyn-dyn-review-loop-routing: **Suggested fix:** Narrow that bullet to voter/coder/research lanes that still waterfall, and state explicitly that `/review`, `/implement` Step 5, and `/design` plan-review **reviewer** panels dispatch with `--no-fallback` and converge on prune-to-empty under cap 2.
  - From dyn-dyn-review-loop-routing: **Suggested fix:** Rewrite the `/design` plan-review sentence to match the no-fallback, drop-row contract and point readers to `docs/review-agents.md` for the current panel matrix.


