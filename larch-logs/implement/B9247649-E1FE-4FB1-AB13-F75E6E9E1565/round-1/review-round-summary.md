# Review Round 1

- Mode: `diff`
- 1 accepted, 4 rejected (1 neutral)

## Accepted Findings

### FINDING_7: Static coverage over-excuses archetypes with mixed straggler and real failures
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt, dyn-cutoff-timing-output.txt, dyn-coverage-gates-output.txt
- **Severity**: important
- **Concern**: `_straggler_excused_static_slugs` excuses an entire archetype slug whenever any static slot row has `reason=straggler-dropped`, and `_static_coverage_reason` subtracts that slug from `missing` unconditionally. On round-1 hard panels with dual vendors per archetype (Codex + Cursor, `--no-fallback`), one vendor can fail for a real reason (`collector-failure`, `result-gate-miss`, `empty`, `NOT_SUBSTANTIVE`) while the peer is straggler-cut; the slug is still excused, so `COVERAGE_GATE_OK=true` even though no successful review exists for that archetype and `review_core` proceeds without its input. `check_reviewer_failure_threshold` may still count the genuine failure, but coverage math removes the slug entirely.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Build coverage by manifest slug and excuse a missing slug only when every launched static slot for that slug that lacks success was dropped for `straggler-dropped`; keep the archetype missing when any non-straggler failure/drop exists.
  - From dyn-cutoff-timing-output.txt: Excuse a slug only when the straggler drop is the sole launched path for that archetype (for example, no peer in `success`, and no non-straggler drop row for the same slug in `DROPPED_SLOTS_FILE` / collector failures that should still block coverage). The existing unit/integration tests cover sole-vendor excusal only.
  - From dyn-coverage-gates-output.txt: Build per-slug drop reason sets from `DROPPED_SLOTS_FILE` and excuse only slugs whose static rows are exclusively `straggler-dropped` (e.g. `excused = straggler_slugs - genuine_failure_slugs`), or excuse only when the manifest shows a single vendor for that archetype. Add a `test_review_pipeline.py` case: dual-vendor archetype with one `straggler-dropped` and one `collector-failure` row must keep `COVERAGE_GATE_OK=false` while `test_check_reviewer_failure_threshold_ignores_straggler_drops` stays green for sole-straggler rows.


