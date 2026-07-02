# Review Round 2

- Mode: `diff`
- 2 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: merged/done resume paths skip stalled-summary reconciliation
- **Reviewer(s)**: cursor-specialist-correctness, dyn-dyn-recovery-logs
- **Severity**: important
- **Concern**: When `resume.start == "done"` or `resume.start == "merged"`, `run_ship` returns success or enters postmerge without calling `reconcile_committed_stalled_summary_if_recovered`. A session that previously committed a genuine stalled `final-summary.md` snapshot can resume after external or partial recovery with durable `done`/`merged` signals while git still records `Outcome: stalled`, even though live normalization would classify the run as shipped. Postmerge flush is tmpdir-only, so the git-tracked summary can remain stalled while ship returns OK.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Call reconcile_committed_stalled_summary_if_recovered on merged/done resume before postmerge/OK when repo summary is stalled and live state normalizes to a recovered outcome; preserve fail-closed push behavior
  - From dyn-dyn-recovery-logs: Run the same guarded reconciliation helper on `done` and `merged` resume success paths when `_committed_summary_heading_is_stalled` is true and `_live_recovered_outcome` is `pr-created`, `pr-created-draft`, or `merged`, with the same fail-closed push behavior as the other call sites.


### FINDING_2: Committed-summary gate can falsely clear stalled state
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, dyn-dyn-recovery-logs
- **Severity**: important
- **Concern**: `_read_committed_final_summary_text` / `_committed_summary_heading_is_stalled` can report "not stalled" when git history, the remote branch, or unpushed local state still reflects a stalled outcome. Mechanisms include: falling back to tmpdir copy after round-1 tmpdir-vs-repo fixes; preferring the working-tree file over `HEAD` so a failed `_commit_run` after `flush_logs_pre` leaves `HEAD` stalled while the gate reads a corrected working tree; and treating local working-tree or local `HEAD` as proof the remote log is repaired after a reconciliation commit succeeds locally but `push_branch` fails, causing the next run to skip reconciliation and return early `OK` while the PR remote still shows `Outcome: stalled`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Limit the gate to repo working-tree/HEAD evidence; do not use tmpdir as a gate input for committed-summary detection
  - From codex-specialist-correctness: Track a failed reconciliation push as needing a retry, or compare/push the local head against the PR head before early `OK`; require one successful idempotent push when a local correction commit may be unpushed.
  - From dyn-dyn-recovery-logs: Treat `git show HEAD:<rel>` as the primary committed source when the path exists at `HEAD`; use the working-tree file only when there is no `HEAD` revision yet. For the gate, consider the summary stalled if `HEAD` still ends in `— stalled`, even when the working tree was updated by a failed commit attempt.


