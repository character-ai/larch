### FINDING_22: Fail closed when run-step3 scope-anchor handoff validation rejects a non-empty path
- **Reviewer(s)**: dyn-scope-flow-output.txt
- **Severity**: important
- **Concern**: `validate_scope_anchor_handoff` clears invalid `SCOPE_ANCHOR_FILE` with only a warning, creating asymmetry where external judges saw anchored scope but MainAgent fallback may not.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-scope-flow-output.txt: Fail closed with a dedicated `LOOP_STATUS` / `TALLY_PLAN_REVIEW_STATUS` when a non-empty handoff path cannot be validated, or fall back to the canonical staged file `$DESIGN_TMPDIR/plan-review-scope-anchor.txt` when it exists and is a regular file under the design tmpdir, instead of clearing the key.



