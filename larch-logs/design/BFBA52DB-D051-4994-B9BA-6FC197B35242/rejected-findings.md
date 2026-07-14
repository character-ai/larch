### [Plan Review] FINDING_2

### FINDING_2: Changed launcher-exit semantics
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Concern**: Replacing the in-process Codex launcher may lose `resolve_launcher_exit` handling, changing failure return codes, `.done` contents, and quiet-mode behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: After `run_vendor_launch`, call `resolve_launcher_exit` against the raw output path (and any retained capture text), write `.done` from the resolved exit, and return that launcher exit; add parity tests for non-zero `.done` and sidecar-preferred failure tails.


### [Plan Review] FINDING_4

### FINDING_4: Negotiation home cleanup leak
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Concern**: `VendorFamilyHooks` lacks a cleanup slot, so auth preflight refusal inside `run_vendor_launch` could bypass caller cleanup and leak temporary `larch-codex-negotiation-home-*` directories.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Pin negotiation migration to caller-side `mkdtemp` + `try/finally shutil.rmtree` around the whole launch (including shared preflight refusal), or an equivalent explicit cleanup contract in `run_negotiation_round`

