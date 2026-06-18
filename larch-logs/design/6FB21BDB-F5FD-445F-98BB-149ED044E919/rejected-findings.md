### [Plan Review] FINDING_2

### FINDING_2: Auto-continuation calls missing on-disk `design-step3-state.sh` instead of plan-review CLI
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: On `PLAN_REVIEW_CONTINUE=true`, the loop still shells out to `skills/design/scripts/design-step3-state.sh`, which is not present on disk (embed-only). The call is suffixed with `|| true`, so stale `.completed/step-3-terminal` and `.step3-terminal-persisted-this-run` are never cleared on multi-round continuation even if terminal-sentinel logic is added elsewhere.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Repoint the continuation branch to python3 "$PLUGIN_ROOT/python/cli.py" plan-review step3-state --design-tmpdir "$DESIGN_TMPDIR" --auto-continuation-entry (matching design-step3-continuation-entry.sh) and add a loop harness assertion that pre-seeded terminal sentinels are removed


