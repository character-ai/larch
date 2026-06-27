### OOS_1: [OUT_OF_SCOPE] Step 2b dirty-detection and baseline-arg test gaps
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing
- **Severity**: latent
- **Concern**: No focused or direct unit tests for `_detect_step2b_drafter_dirty_block`’s `elif` missing-sidecar path (`missing-sidecar-positive-baseline-delta`, `elif` + `st_size > 0` + git porcelain compare) or for `_step2b_drafter_baseline_arg` git-status-failure unlink / no `--baseline-porcelain` behavior. The plan marked these optional; existing integration tests cover sidecar-present dirty recovery but not the extracted seams. Logic appears faithfully extracted and the targeted suite passes; regression risk is test-gap only, not a demonstrated logic bug in the diff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] Weak dirty-tree recovery test assertions
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: `test_step2b_drafter_emits_dirty_tree_recovery` (`python/test_design_lifecycle.py:4641-4676`) only asserts action emission and that `dirty-tree-detected.env` exists; it does not pin `STATUS`/`STAGE`/`RECOVERY_REQUIRED`/`REASON` or the exact recovery warning string the plan called out as optional coverage. Pre-existing weak assertion; implementation at `design_lifecycle.py:3991-3995` matches pinned literals and was not introduced by this diff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.

### OOS_3: [OUT_OF_SCOPE] Untested Codex token sidecar on skip paths
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: Codex token sidecar append on skip paths (`skip_reason` set, `drafter_rc == 2`) at `python/larch/design/design_lifecycle.py:4053-4054` is untested at unit level. Optional plan item; orchestration order preserved vs monolith; no evidence of behavioral drift in existing Step 2b tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.

---

**Subsumed (not emitted as separate findings):** Commit-scope headers (`25ef49790`, `a8db4f118`, `2ac98549b`), orchestration-order attestations, pinned-contract preservation notes, pause-path behavior, gates/ordering, dirty-tree probe shape, action-emission routing, prepare/env sync, and test-coverage positive notes were treated as verification prose, not distinct behavioral risks requiring separate fixes. They are reflected where relevant in **FINDING_1** (complexity/baseline) or dropped as non-actionable affirmations.
