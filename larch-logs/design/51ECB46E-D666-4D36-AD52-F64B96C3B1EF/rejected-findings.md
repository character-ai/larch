### [Plan Review] FINDING_7

### FINDING_7: Golden stdout-order tests lack pre-refactor baseline capture
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: Golden stdout-order smoke tests lack a pre-refactor baseline capture step. The plan requires full-line-order golden smoke tests for nine `review_core` branches and states batch emission must mirror per-branch order. It does not require recording current stdout from `review_core` (or `review_core_capture`) before the refactor. Row-level `_review_core_body` tests can pass while emit order regresses, breaking `review_and_fix.review_core_capture` and Step 5 parsers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add an implementation-order step 0 (or phase 1 sub-step): capture pre-refactor golden stdout for each listed branch from current `python/review_pipeline.py`, commit fixtures under `python/test_review_pipeline.py` (or a sibling golden file), then refactor and lock parity against those fixtures.


### [Plan Review] FINDING_8

### FINDING_8:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/review_pipeline.py:51-57
- **Concern**: [SCOPE-REDUCTION] `_record_prune_round` dual return-rows vs emit-flag API adds an unnecessary second path. Scenario: The issue requires separating pure decisions from stdout emission. An optional emit flag preserves a streaming fallback and invites partial refactors that leave duplicate WARN rows in `review_core_capture`.
- **Proposed resolution**: Require `_record_prune_round` to return optional WARN row tuples only; delete the emit-flag alternate and keep all stdout emission in `_emit_review_core_result`. **1. correctness — `python/ship.py:1689-1699`:** `_ship_phase14_rebase` must retain the post-success `_write_ship_state(phase="ci-initial", ...)` write, not only local counter/handoff mutations. **2. correctness — `python/review_pipeline.py:45-46`:** `dispatch_scout_rows` must snapshot the entire `2078-2086` dispatch prefix, not just the three named scout keys. **3. architecture — `python/review_pipeline.py:51-57`:** Drop the `_record_prune_round` emit-flag alternate; return-rows only.


### [Plan Review] FINDING_9

### FINDING_9:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/ship.py:1364-2148
- **Concern**: [SCOPE-REDUCTION] ship helper extraction over-serves the KEY=value split; run_ship already returns ShipResult and emit_result is already the thin output layer. Scenario: The plan adds _ship_rebase_phase, _ship_phase14_rebase, _ship_postmerge_phase, and ship tests even though this path already has a non-stdout core and separate emitter; that adds merge-loop churn without being required for the emission-separation feature
- **Proposed resolution**: Remove python/ship.py and python/test_ship.py changes from this PR, or limit ship work to documenting/testing the existing run_ship/emit_result seam; track merge-loop helper extraction separately


