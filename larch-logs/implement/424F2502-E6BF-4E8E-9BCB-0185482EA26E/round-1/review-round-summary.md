# Review Round 1

- Mode: `diff`
- 1 accepted, 1 rejected (1 neutral)

## Accepted Findings

### FINDING_10: Step 5c missing-script guidance fires on non-script publish_rc=4 failures
- **Reviewer(s)**: dyn-publish-tail-output.txt
- **Severity**: important
- **Concern**: The new Step 5c paragraph is wired into the shared `VALIDATE_STATUS=defects-found` operator flow, but `publish_core` also returns `publish_rc=4` for non-script failures (empty/missing `composed-plan.md`, review-provenance refusal). Those branches emit `VALIDATE_STATUS=defects-found` with `VALIDATE_MISSING_SCRIPT_COUNT=0` and, on the provenance path, no `VALIDATE_LOG_FILE`. Step 5c still emits `STEP5C_STATUS=validator-defects` for every `publish_rc=4`, so the orchestrator can hit the new missing-script false-positive guidance and the ordinary auto-repair / Fix-and-retry / Override path for failures that are not script-validation defects.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-publish-tail-output.txt: Gate the Step 5c missing-script paragraph on `VALIDATE_MISSING_SCRIPT_COUNT` being a positive integer (or on `kind=missing-script` lines in `VALIDATE_LOG_FILE`). Keep the existing missing-composition and provenance special cases as separate branches; do not treat provenance `rc=4` as a plan-command validator defect.


