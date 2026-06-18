### FINDING_1: Status port must use quiet_init / emit_kv stdout contract
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The planned `status_check_main` port must match the machine-readable stdout contract that `skills/status/scripts/status.sh` and other agent CLI mains already use. Today `status.sh` calls `larch_quiet_init` and emits eight contract keys via `emit_kv`; the `/status` skill parses KVs from stdout only. A `status_check_main` that uses plain `print` or stderr diagnostics can interleave non-KV lines, breaking KV parsing and skill rendering.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add an explicit requirement: status_check_main must call logging_util.quiet_init and emit the eight contract keys only through logging_util.emit_kv (same pattern as check_reviewers_main / degraded_tools_gate_main)

### FINDING_2: review-design-step3-loop.sh edits require _LEGACY_ASSETS blob regeneration
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: blocking
- **Concern**: If the plan updates on-disk `review-design-step3-loop.sh` for `write-design-round-meta` cutover but omits regenerating the gzip `_LEGACY_ASSETS` blob, production `/design` Step 3 still runs the stale embedded loop. Live Step 3 delegates through `plan_review._run_legacy()`, which skips linking on-disk `skills/design/scripts` for `review-design-step3-loop.sh` (it is in `_RETIRE_DESIGN_SKIPS`) and overwrites the materialized script from `_LEGACY_ASSETS`. Deleting `scripts/write-design-round-meta.sh` while the stale embedded loop still defaults to that path leaves the `[[ -x "$_rmd_sh" ]]` gate false and post-revise `round-meta.json` refresh silently stops.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add ### UPDATED: python/plan_review.py to regenerate the embedded skills/design/scripts/review-design-step3-loop.sh asset from the edited live script per docs/python-migration.md C3a1; keep test_embedded_review_design_step3_loop_matches_live_script passing
