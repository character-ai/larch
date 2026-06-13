# Review Round 1

- Mode: `diff`
- 1 accepted, 3 rejected (0 neutral)

## Accepted Findings

### FINDING_9: pause-handling regression on combined Step 6 entry path
- **Reviewer(s)**: dyn-race-guard-output.txt
- **Severity**: important
- **Concern**: The new in-flight guard runs before any `.pause-requested` handling in `skills/design/scripts/design-step6-prelude.sh:88-92`, while `design-step6-cleanup.sh` still checks pause first (line 89) and only then the in-flight guard (lines 90–93). `design-step6.sh` always invokes the prelude before cleanup with `set -euo pipefail`, so when Step 5c is still running (`.bg-wait-active` present, no `.design-step5c-status.env`) and a pause was requested, the prelude now exits 1 with the in-flight error and cleanup never runs. Before this change, the prelude soft-skipped on a missing sidecar and cleanup could still `exec design-pause-save.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-race-guard-output.txt: Add the same early pause checkpoint used in `design-step6-cleanup.sh` immediately before the in-flight guard in `design-step6-prelude.sh` (after `design_source_env_optional`), so pause wins over the in-flight hard error in both wrappers; add a harness case with `.pause-requested` plus `.bg-wait-active` and no sidecar asserting prelude/cleanup route to pause-save instead of exit 1.


