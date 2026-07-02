# Review Round 1

- Mode: `diff`
- 2 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Reconciliation gates on tmpdir `final-summary.md` instead of git-tracked run log
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, codex-specialist-edge-cases, dyn-dyn-recovery-logs
- **Severity**: important
- **Concern**: `_committed_summary_heading_is_stalled` reads only the session tmpdir copy of `final-summary.md`, not the git-tracked run log at `cwd/larch-logs/implement/<run_id>/final-summary.md` (working tree or HEAD) that reconciliation is meant to repair. After a stall snapshot is committed, a resumed session with a fresh tmpdir (no copied larch-logs), or intervening `flush_logs_pre` / `write_final_report` that refreshes only the tmpdir copy, can leave `_live_recovered_outcome` truthy while the gate returns false, so `reconcile_committed_stalled_summary_if_recovered` is skipped and `run_ship` returns OK (and may call `merge.merge_pr`) while the branch still shows Outcome: stalled. If a reconciliation commit succeeds locally but `push_branch` fails, the tmpdir can be corrected while the remote log stays stalled; the next resume may skip reconciliation and return OK without pushing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Read stalled heading from repo larch-logs/implement/<run_id>/final-summary.md (working tree or HEAD), with tmpdir as fallback.
  - From codex-specialist-correctness: Gate on cwd/larch-logs/implement/<run_id>/final-summary.md and retry/push prior run-log-reconciliation-push failures before early OK returns.
  - From codex-specialist-edge-cases: Check cwd/larch-logs/implement/<run_id>/final-summary.md, or check both repo and tmpdir summaries, before deciding reconciliation is unnecessary.
  - From dyn-dyn-recovery-logs: Base the gate on the repo working-tree or `HEAD` copy under `cwd/larch-logs/implement/<run_id>/final-summary.md` (or treat reconciliation as needed whenever live normalization is recovered and either tmpdir or repo copy is still stalled), and add a regression where tmpdir is corrected but `HEAD` remains stalled.


### FINDING_3: Manifest-only backstop rewrites stalled summary without live failure-signal gating
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-edge-cases, dyn-dyn-recovery-logs
- **Severity**: important
- **Concern**: The writer-side manifest-only backstop (`_reconcile_stalled_summary_backstop` in `run_log_flush.py` and `reconcile_stalled_summary_from_manifest` in `final_report.py`) can rewrite a stalled summary to `merged` from manifest evidence alone (`status=done` + `pr_number`) without consulting live ship/finalize failure signals. Although `write_final_report` restricts manifest-only outcome override to the no-state-file case via `_outcome_with_manifest_only_backstop`, `_reconcile_stalled_summary_backstop` runs afterward without that guard. If ship/finalize state files still show active failure and normalization renders `stalled`, a stale `manifest.json` with `status=done` can force a `merged` heading and delete the stalled outcome bullet, including under `strict_final_report=True` where the helper raises only when rewrite fails, not when rewrite would be unsafe.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Require clean ship recovery evidence before manifest-only rewrite, matching _normalize.py gates.
  - From codex-specialist-edge-cases: Gate manifest-only reconciliation on both ship-pr-state.sh and finalize-state.sh being absent or empty, or make the helper skip whenever live state rows exist.
  - From dyn-dyn-recovery-logs: Reuse the same "no active failure signal" predicate as `_has_clean_ship_recovery_evidence` / `_ship_has_active_failure_signal` (or skip manifest rewrite whenever ship/finalize rows exist), and add a test with `status=done` manifest + active `BAIL_REASON` where the summary must stay `stalled`.


