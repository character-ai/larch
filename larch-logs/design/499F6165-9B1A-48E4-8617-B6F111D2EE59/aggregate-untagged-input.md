### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: plan.txt:98-104
- **Concern**: Prior FINDING_4 fix incomplete: Approach `_post_gate_panel_failed_exit` sample still omits required `_core_common_rows` kwargs and `_flush_round_log`. Scenario: The Files section (plan.txt:164-167) specifies the correct helper, but the Approach code sample still shows only `status="panel-failed"` and no flush call. A top-down implementer can copy the broken sample and hit `TypeError` on every post-gate `panel_failed` exit.
- **Proposed resolution**: Replace the Approach sample (plan.txt:98-104) with the complete `_post_gate_panel_failed_exit` body from plan.txt:164-167, or delete the sample and point only to the Files contract.

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:31-32
- **Concern**: Pre-aggregate snapshot write failure omits `_flush_round_log` before `panel_failed` return. Scenario: Lines 31 and 172 require `findings-pre-aggregate-snapshot-failed` before aggregate runs, but unlike threshold `panel_failed` at review_pipeline.py:2277 they do not call `_flush_round_log`. Collect/threshold artifacts can stay tmpdir-only, so committed implement run logs cannot reconstruct the failed round.
- **Proposed resolution**: Route pre-aggregate snapshot `OSError` through the same structured exit as other `panel_failed` paths: `_flush_round_log` first, then `_core_common_rows` with all required kwargs and `threshold_reason=findings-pre-aggregate-snapshot-failed`. Add a test asserting flush on this path (extend plan.txt:267-268).

### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: plan.txt:182
- **Concern**: Empty-merge gated-ballot promote to `findings.md` has no fail-closed error handling. Scenario: When `MERGED_COUNT=0` and `gate.remaining_count > 0`, the plan copies the gated snapshot into `findings.md` then falls through to proposer-map/voters. A failed promote leaves attestation-only `findings.md`, so voters dispatch on an empty or wrong ballot while `PRE_VOTE_*` rows claim in-scope findings remain.
- **Proposed resolution**: Wrap the promote copy in fail-closed handling: on `OSError`, append to `execution-issues.md`, extend existing `rows` with `_pre_vote_gate_rows(gate)`, and return via `_post_gate_panel_failed_exit(..., threshold_reason="pre-vote-oos-gate-ballot-promote-failed")`. Add an integration test for promote copy failure on the empty-merge mixed in-scope path.

### FINDING_4:
- **Reviewer(s)**: Codex-Arch
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/review_pipeline.py:2328-2330
- **Concern**: Empty-merge survivor copy-back is not fail-closed. Scenario: On `MERGED_COUNT=0` rounds where the gate leaves in-scope findings, the plan copies the filtered snapshot back into `findings.md` and then continues. If that overwrite raises `OSError`, the code would keep the attestation-only ballot in place and the post-gate proposer-map / voter path would run against the wrong file, dropping surviving findings.
- **Proposed resolution**: Wrap the copy-back in `try/except OSError` and return the same structured `panel_failed` exit used for other gate I/O failures, with gate rows already emitted.

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: plan.txt:100-104
- **Concern**: Approach pseudocode for `_post_gate_panel_failed_exit` still omits required `_core_common_rows` kwargs. Scenario: The snippet shows only `status="panel-failed"` and a bare `return ReviewCoreResult(...)`, contradicting the complete contract at plan.txt:164-167 and `review_pipeline.py:1957`. An implementer copying the Approach block gets `TypeError` on every post-gate `panel_failed` exit.
- **Proposed resolution**: Delete or replace lines 100-104 with the full `_post_gate_panel_failed_exit` body from plan.txt:164-167 (flush, then `_core_common_rows` with `round_num`, `review_tmpdir`, `panel_mode`, `panel_shape`, `threshold_reason`).

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/review_pipeline.py:2297-2428
- **Concern**: Empty-merge survivor path lacks an explicit no-double-gate control-flow contract. Scenario: After `MERGED_COUNT=0` gating copies in-scope blocks into `findings.md`, the plan says to "fall through" to the shared post-gate voter path but does not require a single shared tail or a `gate_already_ran` guard. `_review_core_body` today uses early returns before the inline prune/voter block (~2332+); a naive refactor can re-run `_prune_nit_then_pre_vote_gate`, skip voter dispatch, or duplicate the voter block.
- **Proposed resolution**: Add one named shared tail (e.g. `_review_core_post_gate_voter_path`) invoked from the normal path after gate and from empty-merge only when `gate.remaining_count > 0`, with an explicit rule that the tail must not call `_prune_nit_then_pre_vote_gate` again.

### FINDING_8:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/review_pipeline.py:142-143
- **Concern**: `_apply_pre_vote_oos_gate` ballot rewrite omits `_atomic_write`. Scenario: The plan rewrites `findings_file` in place but does not require atomic persistence. `prune-nit-findings` already uses `_atomic_write` (`review_aggregate.py:928`); `review_pipeline.py` defines `_atomic_write` at :142. A failed mid-write truncate can leave a partial ballot that still reaches proposer-map and voters.
- **Proposed resolution**: Write the gated ballot with `_atomic_write` in `_apply_pre_vote_oos_gate`, matching `prune-nit-findings`.

### FINDING_9:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: plan.txt:182-183
- **Concern**: Empty-merge survivor copy-back is not fail-closed. Scenario: The plan says to copy the gated in-scope snapshot back to `review_tmpdir / "findings.md"` and then continue, but it never says what happens if that overwrite fails. On an attestation-only empty merge with surviving in-scope findings, a failed or partial copy leaves the ballot empty while the code proceeds to proposer-map and voters, so the feature can silently drop findings or dispatch the wrong ballot.
- **Proposed resolution**: Make the copy-back an explicit checked step with the same fail-closed envelope as the other gate I/O paths. On failure, log to `execution-issues.md` and return `panel_failed` instead of continuing.

### FINDING_10:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:182
- **Concern**: python/review_pipeline.py empty-merge survivor path omits fail-closed handling when rewriting findings.md from gated snapshot. Scenario: When MERGED_COUNT=0 leaves attestation-only findings.md but the gated snapshot still has in-scope blocks, the plan copies snapshot content into findings.md then falls through to proposer-map and voters. There is no OSError handling or PreVoteGateError mapping for that copy/rewrite. A disk-full or permission failure leaves findings.md attestation-only/empty while the gated snapshot holds the real ballot, so voter dispatch runs on an empty ballot and in-scope findings are silently dropped despite PRE_VOTE_FINDINGS_REMAINING>0.
- **Proposed resolution**: Add explicit fail-closed contract for the line-182 rewrite: on copy/write failure append to execution-issues.md and route through PreVoteGateError or _post_gate_panel_failed_with_audit (threshold_reason such as pre-vote-oos-gate-ballot-promote-failed); do not continue to proposer-map/voters unless findings.md contains the gated in-scope blocks.

### FINDING_11:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:31-32
- **Concern**: python/review_pipeline.py pre-aggregate snapshot copy failure path omits the flush helper used for sibling snapshot failures. Scenario: The snapshot contract at lines 31-32 and 172 returns a bare structured panel_failed on copy OSError before aggregate runs, but the empty-merge missing-snapshot path at line 177 uses _post_gate_panel_failed_exit (flush-first). Post-gate flush list at lines 88-96 only names empty-merge snapshot failures. A collect with non-empty findings.md that fails to create findings-pre-aggregate.md can exit without _flush_round_log, so collector output and execution-issues forensics stay in the session tmpdir and never reach committed implement round logs.
- **Proposed resolution**: Wire pre-aggregate snapshot copy OSError (lines 31/172) through the same _post_gate_panel_failed_exit helper as line 177 (threshold_reason=findings-pre-aggregate-snapshot-failed), including round_num/panel_mode/panel_shape kwargs; extend Failure modes and tests to assert flush on that pre-aggregate failure path.

### FINDING_13:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: plan.txt:98-104
- **Concern**: Approach pseudocode for `_post_gate_panel_failed_exit` still omits required `_core_common_rows` kwargs. Scenario: Prior round accepted FINDING_4 and the Files section fixes kwargs at plan.txt:164-167, but the Approach block still shows `rows.extend(_core_common_rows(status="panel-failed"))` without `round_num`, `review_tmpdir`, `panel_mode`, `panel_shape`, or `threshold_reason`. An implementer following the Approach snippet will raise `TypeError` on every post-gate `panel_failed` exit.
- **Proposed resolution**: Replace plan.txt:98-104 with the complete `_post_gate_panel_failed_exit` body from plan.txt:164-167 (flush, full `_core_common_rows(...)`, return), or delete the truncated snippet and point only to the Files contract.

### FINDING_14:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:176-182
- **Concern**: Empty-merge gated-snapshot copy into `findings.md` has no fail-closed handling. Scenario: When `MERGED_COUNT=0` and `gate.remaining_count > 0`, the plan gates `findings-pre-aggregate.md` then says to copy the gated ballot into post-aggregate `findings.md` and continue to voters. There is no `OSError` handling for that copy. If the copy fails, `findings.md` stays attestation-only while `PRE_VOTE_*` rows report remaining findings, so voter dispatch can run on an empty ballot and drop in-scope findings the gate kept on the snapshot.
- **Proposed resolution**: Wrap the snapshot-to-`findings.md` copy in fail-closed handling: on `OSError`, log to `execution-issues.md` and return `_post_gate_panel_failed_with_audit(..., threshold_reason="pre-vote-oos-gate-ballot-promote-failed")` (or equivalent structured `panel_failed` with flush). Add an integration test that forces this copy failure and asserts no voter dispatch.
