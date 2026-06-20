# Review Round 2

- Mode: `diff`
- 1 accepted, 3 rejected (0 neutral)

## Accepted Findings

### FINDING_8: Stale step-5c-terminal sentinel on retry
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: Step 5c writes `.completed/step-5c-terminal` on abort paths, but a retry does not clear that terminal sentinel before starting the next background run. Scenario: first attempt hits rc 2/5 and writes the sentinel in `finally`; the operator fixes the issue and re-runs Step 5c; a premature empty notification probe sees the stale sentinel and can parse stale status/output while the new publish is still running.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Remove `.completed/step-5c-terminal` at the start of a fresh Step 5c attempt after `DESIGN_TMPDIR` is validated, before `_bg_wait_marker_context` creates the live marker.


