### FINDING_1: Plan edits live loop script but omits `_LEGACY_ASSETS` re-embed for `review-design-step3-loop.sh`
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Codex-Generic
- **Severity**: blocking
- **Concern**: The plan updates on-disk `skills/design/scripts/review-design-step3-loop.sh` but does not regenerate its gzip embed in `python/plan_review.py` `_LEGACY_ASSETS`. Because `review-design-step3-loop.sh` is listed in `_RETIRE_DESIGN_SKIPS`, `plan-review run` materializes the embedded blob at runtime instead of the edited live file. Fixes such as `step3_loop_write_terminal_step3`, persist-sidecar logic, and hook/SKILL retargeting to `.completed/step-3-terminal` therefore never execute in production; premature-notification recovery remains gated on `.completed/step-3` only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add ### UPDATED: python/plan_review.py re-embedding review-design-step3-loop.sh (decode/edit/re-encode per docs/python-migration.md); require test_embedded_review_design_step3_loop_matches_live_script in Testing strategy
  - From Cursor-Innovation: Add `### UPDATED: python/plan_review.py` to regenerate the embedded `review-design-step3-loop.sh` blob from the updated on-disk script (same contract as `docs/python-migration.md` gzip-shim guidance); keep `test_embedded_review_design_step3_loop_matches_live_script` green
  - From Cursor-Pragmatic: Add `### UPDATED: python/plan_review.py` to regenerate the `review-design-step3-loop.sh` gzip blob from the edited live script (per `docs/python-migration.md`); keep bytes identical to live so the existing embedded/live parity test passes
  - From Codex-Generic: Add ### UPDATED: python/plan_review.py to regenerate or update the _LEGACY_ASSETS blobs for review-design-step3-loop.sh and design-step3-state.sh, and keep the live script plus embedded asset parity test green

### FINDING_2: Auto-continuation calls missing on-disk `design-step3-state.sh` instead of plan-review CLI
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: On `PLAN_REVIEW_CONTINUE=true`, the loop still shells out to `skills/design/scripts/design-step3-state.sh`, which is not present on disk (embed-only). The call is suffixed with `|| true`, so stale `.completed/step-3-terminal` and `.step3-terminal-persisted-this-run` are never cleared on multi-round continuation even if terminal-sentinel logic is added elsewhere.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Repoint the continuation branch to python3 "$PLUGIN_ROOT/python/cli.py" plan-review step3-state --design-tmpdir "$DESIGN_TMPDIR" --auto-continuation-entry (matching design-step3-continuation-entry.sh) and add a loop harness assertion that pre-seeded terminal sentinels are removed

### FINDING_3: Plan omits `_LEGACY_ASSETS` re-embed for `design-step3-state.sh`
- **Reviewer(s)**: Codex-Generic
- **Severity**: blocking
- **Concern**: `_materialize_legacy_root()` skips on-disk `design-step3-state.sh` and writes the `_LEGACY_ASSETS` embed instead. If the plan changes retired Step 3 shell surfaces without updating that embedded blob, runtime plan-review may continue executing stale embedded state logic alongside any live-script edits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Add ### UPDATED: python/plan_review.py to regenerate or update the _LEGACY_ASSETS blobs for review-design-step3-loop.sh and design-step3-state.sh, and keep the live script plus embedded asset parity test green
