### FINDING_1: Missing Codex raw-events fallback
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Concern**: Direct Codex drafter launch may mirror quota data before creating the `{}` raw-events fallback, leaving quota and usage consumers empty on no-event runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add the same pre-mirror fallback step to the direct Codex drafter hook wiring (or shared Codex hook helper) and assert it in `test_external_dispatch.py` drafter coverage.


### FINDING_3: Codex model-argument error regression
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Concern**: Moving Codex model resolution into shared launch hooks may raise or preflight-map `ValueError` instead of preserving the existing pre-launch exit 1 with no `RESPONSE_FILE` KV.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Resolve Codex model args before `run_vendor_launch` (same as the Cursor model-before-runner rule) and keep the existing `_err` + `return 1` path on `ValueError`


