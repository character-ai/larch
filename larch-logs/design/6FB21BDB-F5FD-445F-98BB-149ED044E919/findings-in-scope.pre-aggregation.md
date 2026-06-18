### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/plan_review.py:808-821
- **Concern**: The plan updates on-disk review-design-step3-loop.sh but never lists re-encoding that script in python/plan_review.py _LEGACY_ASSETS. Scenario: plan-review run materializes a legacy root where _RETIRE_DESIGN_SKIPS overwrites the on-disk loop with the embedded gzip body, so step3_loop_write_terminal_step3 and persist-sidecar logic never run at runtime; hook/SKILL changes cannot fix the incident
- **Proposed resolution**: Add ### UPDATED: python/plan_review.py re-embedding review-design-step3-loop.sh (decode/edit/re-encode per docs/python-migration.md); require test_embedded_review_design_step3_loop_matches_live_script in Testing strategy

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/plan_review.py:808-821
- **Concern**: `review-design-step3-loop.sh` is gzip-embedded and listed in `_RETIRE_DESIGN_SKIPS`; runtime `plan-review run` never executes the on-disk loop file the plan edits. Scenario: Edits to `skills/design/scripts/review-design-step3-loop.sh` alone (including `step3_loop_write_terminal_step3` and persist sidecar) do not ship; premature-notification recovery still gates on `.completed/step-3` and never writes `.completed/step-3-terminal`
- **Proposed resolution**: Add `### UPDATED: python/plan_review.py` to regenerate the embedded `review-design-step3-loop.sh` blob from the updated on-disk script (same contract as `docs/python-migration.md` gzip-shim guidance); keep `test_embedded_review_design_step3_loop_matches_live_script` green

### FINDING_3:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/plan_review.py:615-823
- **Concern**: The plan updates live `review-design-step3-loop.sh` but does not regenerate its gzip embed in `_LEGACY_ASSETS`. Scenario: `review-design-step3-loop.sh` is in `_RETIRE_DESIGN_SKIPS`, so `_materialize_legacy_root()` writes only the embedded blob at runtime, not the live file; `step3_loop_write_terminal_step3()` would never run, `test_embedded_review_design_step3_loop_matches_live_script` would fail, and the incident fix would not ship
- **Proposed resolution**: Add `### UPDATED: python/plan_review.py` to regenerate the `review-design-step3-loop.sh` gzip blob from the edited live script (per `docs/python-migration.md`); keep bytes identical to live so the existing embedded/live parity test passes

### FINDING_4:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/review-design-step3-loop.sh:833
- **Concern**: Auto-continuation still shells out to a missing on-disk design-step3-state.sh instead of the plan-review step3-state CLI. Scenario: On PLAN_REVIEW_CONTINUE=true the loop calls skills/design/scripts/design-step3-state.sh which is not present in the repo (embed-only). The call is suffixed with || true so stale .completed/step-3-terminal and .step3-terminal-persisted-this-run are never cleared on multi-round continuation despite FINDING_3/4
- **Proposed resolution**: Repoint the continuation branch to python3 "$PLUGIN_ROOT/python/cli.py" plan-review step3-state --design-tmpdir "$DESIGN_TMPDIR" --auto-continuation-entry (matching design-step3-continuation-entry.sh) and add a loop harness assertion that pre-seeded terminal sentinels are removed

### FINDING_5:
- **Reviewer(s)**: Codex-Generic
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/plan_review.py:808-820
- **Concern**: The plan updates retired Step 3 shell paths but omits the embedded assets used by plan-review. Scenario: _materialize_legacy_root skips design-step3-state.sh and review-design-step3-loop.sh and writes _LEGACY_ASSETS instead; after retargeting the hook to step-3-terminal, live python/cli.py plan-review run would still execute an embedded loop that never writes step-3-terminal or the sidecar, so premature-notification recovery remains blocked
- **Proposed resolution**: Add ### UPDATED: python/plan_review.py to regenerate or update the _LEGACY_ASSETS blobs for review-design-step3-loop.sh and design-step3-state.sh, and keep the live script plus embedded asset parity test green

