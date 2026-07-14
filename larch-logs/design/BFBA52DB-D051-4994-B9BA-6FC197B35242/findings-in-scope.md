### FINDING_1: Missing Codex raw-events fallback
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Concern**: Direct Codex drafter launch may mirror quota data before creating the `{}` raw-events fallback, leaving quota and usage consumers empty on no-event runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add the same pre-mirror fallback step to the direct Codex drafter hook wiring (or shared Codex hook helper) and assert it in `test_external_dispatch.py` drafter coverage.

### FINDING_2: Changed launcher-exit semantics
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Concern**: Replacing the in-process Codex launcher may lose `resolve_launcher_exit` handling, changing failure return codes, `.done` contents, and quiet-mode behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: After `run_vendor_launch`, call `resolve_launcher_exit` against the raw output path (and any retained capture text), write `.done` from the resolved exit, and return that launcher exit; add parity tests for non-zero `.done` and sidecar-preferred failure tails.

### FINDING_3: Codex model-argument error regression
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Concern**: Moving Codex model resolution into shared launch hooks may raise or preflight-map `ValueError` instead of preserving the existing pre-launch exit 1 with no `RESPONSE_FILE` KV.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Resolve Codex model args before `run_vendor_launch` (same as the Cursor model-before-runner rule) and keep the existing `_err` + `return 1` path on `ValueError`

### FINDING_4: Negotiation home cleanup leak
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Concern**: `VendorFamilyHooks` lacks a cleanup slot, so auth preflight refusal inside `run_vendor_launch` could bypass caller cleanup and leak temporary `larch-codex-negotiation-home-*` directories.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Pin negotiation migration to caller-side `mkdtemp` + `try/finally shutil.rmtree` around the whole launch (including shared preflight refusal), or an equivalent explicit cleanup contract in `run_negotiation_round`
