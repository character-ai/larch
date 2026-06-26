### OOS_1: [OUT_OF_SCOPE] stale `voting-tally-degraded-attempt-*.md` siblings at `_run_round` entry
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `_run_round` unlinks `degraded-retry.flag` and `degraded-retry.done` at entry but does not clear prior `voting-tally-degraded-attempt-*.md` siblings. Reusing the same `round-N` directory across Step 5 re-entry can leave a stale `voting-tally-degraded-attempt-2.md` from an earlier degraded→degraded run while a later degraded→clean run overwrites only attempt-1. With the new allowlist glob, that stale file can flush into committed `larch-logs` and mislead post-run analysis.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: At `_run_round` entry, unlink `voting-tally-degraded-attempt-*.md` alongside the retry flags, or scope run-log copy to artifacts produced in the current invocation.
  - From cursor-specialist-testing-output.txt: Unlink `voting-tally-degraded-attempt-*.md` alongside the flag markers at `_run_round` entry, or add a regression test if cleanup is intentionally deferred.

### OOS_2: [OUT_OF_SCOPE] unrelated `complexity-baseline.json` entry removals
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Commit `d1d4fedda` removes hundreds of unrelated complexity-baseline entries (e.g. `admission.py`, `bootstrap.py`, `session_env.py`, `stall_recovery.py`) while only `_run_round` changed for this feature. That weakens complexity enforcement across those modules if the deletions are not backed by real refactors, and materially widens PR churn and merge-conflict surface without aiding the feature.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Regenerate the baseline narrowly for `_run_round` only, or restore unrelated entries.
  - From cursor-specialist-testing-output.txt: Regenerate baseline scoped to `_run_round` only when feasible, or split baseline refresh into a separate commit/PR.

### OOS_3: [OUT_OF_SCOPE] test does not lock in attempt-2 dedup artifact behavior
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `test_parse_failed_warning_surfaces_after_still_degraded_retry` covers identical still-degraded retry bodies but does not assert artifact outcomes (`voting-tally-degraded-attempt-1.md` preserved, `voting-tally-degraded-attempt-2.md` absent when retry content equals attempt-1). A future edit could reintroduce spurious attempt-2 copies without failing CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add `assert not (round_dir / "voting-tally-degraded-attempt-2.md").exists()` to that test.
  - From cursor-specialist-testing-output.txt: Extend that test with `assert (round_dir / "voting-tally-degraded-attempt-1.md").exists()` and `assert not (round_dir / "voting-tally-degraded-attempt-2.md").exists()`.

