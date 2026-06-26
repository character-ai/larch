### OOS_1: [OUT_OF_SCOPE] Zero-drop pre-vote gate clears stale parent OOS audit (plan-aligned)
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing
- **Severity**: nit
- **Concern**: The change removes `gate.dropped_count <= 0` early-return in `_copy_gate_audit_to_parent` and the `if gate.dropped_count > 0:` guard in `_prune_nit_then_pre_vote_gate`, so parent copy runs after every gate. `_apply_pre_vote_oos_gate` still always writes `review_tmpdir/oos-dropped-before-vote.md` (including empty on zero drops), enabling `shutil.copyfile` to overwrite stale parent bytes. `not session_env_path` remains a no-op; copy failure still raises fail-closed `PreVoteGateError`. Security-only and positive public-drop paths are unchanged when `dropped_count > 0`. Production layout (`session-env.sh` in `IMPLEMENT_TMPDIR`, round audit in `round-N/`) avoids same-file copy collisions. Regression test `test_prune_nit_then_pre_vote_gate_clears_stale_parent_audit_when_no_drops` exercises the full path with a seeded stale parent file and asserts zero drops, empty round/parent audits, and unchanged ballot content. New fail-closed copy surface on zero-drop rounds is intentional per plan; existing `test_pre_vote_oos_gate_*` tests and CI remain valid. A separate `chore(larch-logs): flush` commit in the diff is out of scope for code review.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_2: [OUT_OF_SCOPE] Zero-findings branch bypasses parent audit cleanup
- **Reviewer(s)**: codex-generalist, codex-specialist-testing
- **Severity**: important
- **Concern**: When `findings_count == "0"`, `_zero_findings_branch` returns without writing or copying an empty current audit, so an earlier `parent/oos-dropped-before-vote.md` from a prior round with drops can remain visible after a later round with no findings at all. If the stale-clear invariant applies to every no-drop round, this path still leaves the bug open.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generalist: Before returning from the `findings_count == "0"` branch, write an empty `review_tmpdir/oos-dropped-before-vote.md` and copy it to the session parent using the same fail-closed parent-copy path, or run a zero-result gate helper that produces the same empty audit invariant.
  - From codex-specialist-testing: If the invariant is meant to cover every no-drop round, add the same parent overwrite or clear step to `_zero_findings_branch`, or route that branch through the shared cleanup helper.

### OOS_3: [OUT_OF_SCOPE] No test for parent-copy failure on zero-drop rounds
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: No test covers parent-copy failure on zero-drop rounds. An unwritable parent directory on a zero-drop round should raise `pre-vote-oos-gate-parent-copy-failed`, but that behavior is undocumented by tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Add a stub parent dir with chmod 0o444 or similar and assert `PreVoteGateError` `threshold_reason`.

