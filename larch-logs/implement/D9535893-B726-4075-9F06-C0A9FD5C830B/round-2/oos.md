### FINDING_1: [OUT_OF_SCOPE] Failure-path result-env coverage gaps
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-bgjob-kv
- **Severity**: minor
- **Concern**: The preflight, orphan-timeout, and empty-plan failure paths are still mostly validated through stdout-only assertions, so regressions in `.step5-review-result.env` writes on failure branches could slip past CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Extend the empty-plan test to read .step5-review-result.env when tightening coverage later
  - From cursor-specialist-testing: Add result-env assertions if orphan detach becomes a bgjob consumer
  - From dyn-dyn-bgjob-kv: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_2: Normalize replay can rebuild a sparse Step 5 envelope
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing, dyn-dyn-bgjob-kv
- **Severity**: major
- **Concern**: `normalize_status` / `_step5_result_env_rows_from_text` reconstruct `.step5-review-result.env` from a partial allowlist plus fresh difficulty data, so replayed stdout and the merge file can diverge or drop legacy keys like `PANEL_TIER` and `AUDIT_UPGRADE`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-testing: Reuse _step5_envelope_rows with defaults or whitelist all envelope keys including PANEL_TIER and AUDIT_UPGRADE; add a test asserting full stdout/env parity on normalize replay
  - From dyn-dyn-bgjob-kv: When reconstructing from captured stdout, copy every legacy envelope key present in the text (including PANEL_TIER and AUDIT_UPGRADE) into the merge rows; only fall back to _step5_difficulty_rows() for keys absent from the capture, and fail closed if required core keys are missing rather than writing a sparse env.
  - From dyn-dyn-bgjob-kv: Treat incomplete captures as `missing-step5-envelope` (do not write a partial merge file), or default every required legacy key before writing; extend the normalize replay test to assert full envelope parity between stdout and `.step5-review-result.env`.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_3: [OUT_OF_SCOPE] Step 3 merge-file test omits routing keys
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-bgjob-kv
- **Severity**: minor
- **Concern**: The new Step 3 merge-file test does not pin `NEXT_ACTION` and other routing fields, so a regression in `step3_loop_persist_envelope` could still pass while bgjob routing breaks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Add result["NEXT_ACTION"] and other required routing keys in the new merge-file test
  - From cursor-specialist-testing: Assert result["NEXT_ACTION"] and other required routing keys in the new merge-file test
  - From dyn-dyn-bgjob-kv: The new Step 3 merge-file test validates a subset of completion KVs but does not pin routing fields such as `NEXT_ACTION` that downstream bgjob wrappers will need. Key loss there would not fail this harness.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

