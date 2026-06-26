### FINDING_1: Approach `_post_gate_panel_failed_exit` sample omits required kwargs
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Requirements
- **Severity**: blocking
- **Concern**: The Approach pseudocode at plan.txt:98-104 still shows only `status="panel-failed"` (and a bare `return ReviewCoreResult(...)`) without `_flush_round_log` or the full `_core_common_rows` kwargs (`round_num`, `review_tmpdir`, `panel_mode`, `panel_shape`, `threshold_reason`). That contradicts the complete contract at plan.txt:164-167 and `review_pipeline.py:1957`. A top-down implementer copying the Approach block will raise `TypeError` on every post-gate `panel_failed` exit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Replace the Approach sample (plan.txt:98-104) with the complete `_post_gate_panel_failed_exit` body from plan.txt:164-167, or delete the sample and point only to the Files contract.
  - From Cursor-Innovation: Delete or replace lines 100-104 with the full `_post_gate_panel_failed_exit` body from plan.txt:164-167 (flush, then `_core_common_rows` with `round_num`, `review_tmpdir`, `panel_mode`, `panel_shape`, `threshold_reason`).
  - From Cursor-Requirements: Replace plan.txt:98-104 with the complete `_post_gate_panel_failed_exit` body from plan.txt:164-167 (flush, full `_core_common_rows(...)`, return), or delete the truncated snippet and point only to the Files contract.


### FINDING_2: Empty-merge survivor promote copy-back is not fail-closed
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Codex-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: blocking
- **Concern**: When `MERGED_COUNT=0` and the pre-vote gate leaves in-scope findings (`gate.remaining_count > 0`), the plan copies the gated snapshot back into `findings.md` and falls through to proposer-map/voters. That copy/rewrite has no `OSError` handling. On disk-full, permission, or other I/O failure, `findings.md` can remain attestation-only or partial while `PRE_VOTE_*` rows report remaining findings, so voter dispatch runs on the wrong or empty ballot and in-scope findings are silently dropped.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Wrap the promote copy in fail-closed handling: on `OSError`, append to `execution-issues.md`, extend existing `rows` with `_pre_vote_gate_rows(gate)`, and return via `_post_gate_panel_failed_exit(..., threshold_reason="pre-vote-oos-gate-ballot-promote-failed")`. Add an integration test for promote copy failure on the empty-merge mixed in-scope path.
  - From Codex-Arch: Wrap the copy-back in `try/except OSError` and return the same structured `panel_failed` exit used for other gate I/O failures, with gate rows already emitted.
  - From Codex-Innovation: Make the copy-back an explicit checked step with the same fail-closed envelope as the other gate I/O paths. On failure, log to `execution-issues.md` and return `panel_failed` instead of continuing.
  - From Cursor-Pragmatic: Add explicit fail-closed contract for the line-182 rewrite: on copy/write failure append to execution-issues.md and route through PreVoteGateError or _post_gate_panel_failed_with_audit (threshold_reason such as pre-vote-oos-gate-ballot-promote-failed); do not continue to proposer-map/voters unless findings.md contains the gated in-scope blocks.
  - From Cursor-Requirements: Wrap the snapshot-to-`findings.md` copy in fail-closed handling: on `OSError`, log to `execution-issues.md` and return `_post_gate_panel_failed_with_audit(..., threshold_reason="pre-vote-oos-gate-ballot-promote-failed")` (or equivalent structured `panel_failed` with flush). Add an integration test that forces this copy failure and asserts no voter dispatch.


