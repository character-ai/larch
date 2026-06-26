### OOS_1: [OUT_OF_SCOPE] Non-`ok` aggregate outcomes still bypass the pre-vote gate
- **Description**: [OUT_OF_SCOPE] Non-`ok` aggregate outcomes still bypass the pre-vote gate. Scenario: `dispatch-failed`, `insufficient-input`, `validation-failed`, and `disabled` leave `findings.md` unchanged and today fall through to inline prune/voters (~2332). The plan gates only normal, validation-exhausted, and empty-merge branches, so OOS-titled blocks on those fallthrough paths still reach voters.
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/review_pipeline.py:2332
- **Phase**: design



### OOS_2: [OUT_OF_SCOPE] `_apply_pre_vote_oos_gate` ballot rewrite omits atomic persistence
- **Description**: [OUT_OF_SCOPE] `_apply_pre_vote_oos_gate` ballot rewrite omits atomic persistence. Scenario: `prune-nit-findings` already uses `_atomic_write` for ballot rewrites; the plan specifies in-place rewrite without atomic durability. A mid-write failure can truncate `findings.md` while the round continues to proposer-map/voters.
- **Reviewer**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/review_aggregate.py:928
- **Phase**: design



### OOS_3: Aggregate non-`ok` fallthrough paths still bypass the pre-vote gate
- **Description**: Aggregate non-`ok` fallthrough paths still bypass the pre-vote gate. Scenario: When aggregation returns `dispatch-failed`, `insufficient-input`, `disabled`, or `validation-failed`, control still reaches today's inline prune/voter tail with unchanged `findings.md`. OOS-titled FINDING blocks on those paths still reach voters, so the structural brake misses real code paths the issue targets.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: correctness
- **Location**: python/review_pipeline.py:2332
- **Phase**: design



### OOS_4: Parent `oos-dropped-before-vote.md` can retain stale drops on zero-drop rounds
- **Description**: Parent `oos-dropped-before-vote.md` can retain stale drops on zero-drop rounds. Scenario: `_copy_gate_audit_to_parent` copies only when `dropped_count > 0` and never clears the implement parent file when a later round drops nothing. Operators can read stale OOS drops from a prior round.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: python/review_pipeline.py:1796-1799
- **Phase**: design



### OOS_5: Pre-aggregate snapshot copy failure omits `_flush_round_log`
- **Description**: Pre-aggregate snapshot copy failure omits `_flush_round_log`. Scenario: Snapshot `OSError` before aggregate returns bare `ReviewCoreResult(2, panel_failed, ...)` while other `panel_failed` paths use `_post_gate_panel_failed_exit` with flush first. Collect/dispatch artifacts may stay tmpdir-only in committed run logs.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: plan.txt:31-32
- **Phase**: design



