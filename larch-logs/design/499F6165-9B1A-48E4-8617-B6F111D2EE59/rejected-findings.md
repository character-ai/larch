### [Plan Review] FINDING_3

### FINDING_3: Pre-aggregate snapshot write failure omits `_flush_round_log`
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The pre-aggregate snapshot contract at plan.txt:31-32 and 172 returns a bare structured `panel_failed` on copy `OSError` before aggregate runs, without calling `_flush_round_log`. Unlike the empty-merge missing-snapshot path (line 177) and sibling threshold `panel_failed` paths (e.g. `review_pipeline.py:2277`), collect/threshold artifacts can stay tmpdir-only, so committed implement run logs cannot reconstruct the failed round.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Route pre-aggregate snapshot `OSError` through the same structured exit as other `panel_failed` paths: `_flush_round_log` first, then `_core_common_rows` with all required kwargs and `threshold_reason=findings-pre-aggregate-snapshot-failed`. Add a test asserting flush on this path (extend plan.txt:267-268).
  - From Cursor-Pragmatic: Wire pre-aggregate snapshot copy OSError (lines 31/172) through the same _post_gate_panel_failed_exit helper as line 177 (threshold_reason=findings-pre-aggregate-snapshot-failed), including round_num/panel_mode/panel_shape kwargs; extend Failure modes and tests to assert flush on that pre-aggregate failure path.


### [Plan Review] FINDING_4

### FINDING_4: Empty-merge survivor path lacks explicit no-double-gate control-flow contract
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: After `MERGED_COUNT=0` gating copies in-scope blocks into `findings.md`, the plan says to "fall through" to the shared post-gate voter path but does not require a single shared tail or a `gate_already_ran` guard. `_review_core_body` today uses early returns before the inline prune/voter block (~2332+); a naive refactor can re-run `_prune_nit_then_pre_vote_gate`, skip voter dispatch, or duplicate the voter block.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add one named shared tail (e.g. `_review_core_post_gate_voter_path`) invoked from the normal path after gate and from empty-merge only when `gate.remaining_count > 0`, with an explicit rule that the tail must not call `_prune_nit_then_pre_vote_gate` again.


### [Plan Review] FINDING_5

### FINDING_5: `_apply_pre_vote_oos_gate` ballot rewrite omits `_atomic_write`
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The plan rewrites `findings_file` in place during `_apply_pre_vote_oos_gate` but does not require atomic persistence. `prune-nit-findings` already uses `_atomic_write` (`review_aggregate.py:928`); `review_pipeline.py` defines `_atomic_write` at :142. A failed mid-write truncate can leave a partial ballot that still reaches proposer-map and voters.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Write the gated ballot with `_atomic_write` in `_apply_pre_vote_oos_gate`, matching `prune-nit-findings`.


### [Plan Review] FINDING_6

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/review_pipeline.py:126-143
- **Concern**: [SCOPE-REDUCTION] Planned `_renumber_finding_blocks` duplicates `review_aggregate._renumber_findings`. Scenario: The plan adds `_renumber_finding_blocks` even though `review_aggregate._renumber_findings` already splits with `parse_findings_text(..., boundary="any_heading")` and rewrites `### FINDING_N:` headings identically (`review_aggregate.py:603-606`). Two renumber helpers drift on heading grammar changes.
- **Proposed resolution**: Call `review_aggregate._renumber_findings` (or move one shared helper) instead of adding `_renumber_finding_blocks`.


### [Plan Review] FINDING_7

### FINDING_7:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: code-quality
- **Location**: plan.txt:42-47
- **Concern**: [SCOPE-REDUCTION] Add an optional prefix_rows hook to _zero_findings_branch. Scenario: The caller already owns rows and can prepend gate rows before calling _zero_findings_branch. The extra parameter never changes emitted output, but it widens the contract and test surface.
- **Proposed resolution**: Remove prefix_rows and keep row concatenation in the caller.


