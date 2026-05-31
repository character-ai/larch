### [Plan Review] FINDING_2

### FINDING_2: failure_reason must use head-changed-after-dispatch, not head-changed
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Concern**: The plan’s `failure_reason` / `FixOutcome` handling uses `head-changed` instead of the Bash status `head-changed-after-dispatch`. In `run_check_fix_loop`, vendor HEAD moves after dispatch will not map to terminal `head-changed` / `TRANSIENT`; they will be misclassified as `dispatch-failed`. Bash maps the post-dispatch status to the outer `head-changed` terminal class only after recognizing `head-changed-after-dispatch` (see `scripts/ship-pr.sh:202-203` and `scripts/lint-fix-loop.sh:436-451`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Match `scripts/ship-pr.sh:202-203` and `scripts/lint-fix-loop.sh:436-451`; use `head-changed-after-dispatch` in `FixOutcome` and loop handling

