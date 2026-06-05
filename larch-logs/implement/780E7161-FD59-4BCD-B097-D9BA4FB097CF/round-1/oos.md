### FINDING_11: [OUT_OF_SCOPE] PR_NUMBER/REPO not validated before gh api path build
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-api-input-safety-output.txt
- **Severity**: latent
- **Concern**: At `scripts/compute-pr-line-counts.sh:33-42` (and call sites in `write-final-report.sh`), `PR_NUMBER` and `REPO` are interpolated into the `gh api` REST path with only empty/`0` skipping. There is no `^[0-9]+$` check on `PR_NUMBER` and no `validate_repo`-style guard on `REPO`. In normal runs values come from session setup / create-pr, but tampered `ship-pr-state.sh`, `session-env.sh`, or direct CLI invocation could supply odd values and trigger unexpected `gh api` paths or failures (degraded to `N/A`, not RCE).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Reject values that do not match `^[0-9]+$` for `--pr-number` and `^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$` for nonempty `--repo` before calling `gh`, mirroring the `RUN_ID` rejection pattern in `write-final-report.sh`.
  - From dyn-api-input-safety-output.txt: Before building `endpoint`, reject non-digit `PR_NUMBER` (emit `LINES_STATUS=skipped` with `REASON=invalid-pr` or `unavailable`) and apply the existing `validate_repo` pattern used in `scripts/upsert-diagrams-comment.sh:116-124` for nonempty `REPO`; mirror the same checks in `skills/implement/scripts/write-final-report.sh:118-119` before invoking the helper, consistent with `RUN_ID` path rejection at `write-final-report.sh:79-83`.


Vote tally: YES=1 NO=0 EXON=0 JUDGE_ERROR=2 Result=rejected

### FINDING_12: [OUT_OF_SCOPE] write-final-report validates RUN_ID but not PR_NUMBER/REPO at new gh call site
- **Reviewer(s)**: dyn-api-input-safety-output.txt
- **Severity**: latent
- **Concern**: `skills/implement/scripts/write-final-report.sh:79-83` fail-closes on path-metacharacters in `RUN_ID` but do not apply analogous validation to `PR_NUMBER`/`REPO` at the new helper call site (`118-119`); pre-existing gap amplified by this branch’s first `gh api` use from final-report wiring.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-api-input-safety-output.txt: (Covered by FINDING_11 dyn-api fix — mirror `RUN_ID` rejection and `validate_repo` at the `write-final-report.sh` call site before invoking the helper.)

Vote tally: YES=1 NO=0 EXON=0 JUDGE_ERROR=2 Result=rejected

