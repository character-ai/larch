### [Plan Review] FINDING_1

### FINDING_1: Coder apply timing ledger must be explicitly resolved and injected, overriding stale parent env
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: Codex apply timing is recorded inside `launch-codex-exec`, not by a separate post-call helper. If the `_run()` call that invokes `launch-codex-exec` does not receive an explicit `env=` carrying the resolved ledger (and correct tmpdir keys), codex-only apply can emit no chartable vendor row (same failure mode as a live run when Cursor is skipped). Separately, `_resolve_coder_timing_ledger` must win over stale parent env: when standalone `/review` or a nested caller still has `IMPLEMENT_TMPDIR` in `os.environ`, `resolve_timing_ledger_path` inside `launch-codex-exec` can append the `codex-review-fix` row to the wrong `timing-ledger.tsv` even when a local resolver exists.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Require an explicit env={**os.environ, LARCH_TIMING_LEDGER: str(resolved), IMPLEMENT_TMPDIR/REVIEW_TMPDIR: ...} argument on the _run() that invokes launch-codex-exec; keep --timing-task-kind codex-review-fix unchanged
  - From Cursor-Innovation: Build one env dict from the resolved ledger path and pass it to both launch-codex-exec and _record_coder_vendor_task; set LARCH_TIMING_LEDGER to the resolved path and avoid relying on ambient IMPLEMENT_TMPDIR for ledger selection


