### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/review_and_fix.py:1289-1316
- **Concern**: Codex apply timing is written inside launch-codex-exec, not by a separate post-call helper. Scenario: Plan says to export LARCH_TIMING_LEDGER for codex but only adds post-call _record_coder_vendor_task for Cursor; launch-codex-exec already calls timing record-vendor-task without --ledger, so if the launch-codex-exec _run() call does not receive env= with the resolved ledger, codex-only apply still writes nowhere chartable (same failure mode as the live run when Cursor is skipped)
- **Proposed resolution**: Require an explicit env={**os.environ, LARCH_TIMING_LEDGER: str(resolved), IMPLEMENT_TMPDIR/REVIEW_TMPDIR: ...} argument on the _run() that invokes launch-codex-exec; keep --timing-task-kind codex-review-fix unchanged

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/review_and_fix.py:24-43
- **Concern**: _resolve_coder_timing_ledger must win over stale parent env keys. Scenario: When standalone /review or a nested caller still has IMPLEMENT_TMPDIR in os.environ, resolve_timing_ledger_path inside launch-codex-exec can append the codex-review-fix row to the wrong timing-ledger.tsv even after a local resolver exists
- **Proposed resolution**: Build one env dict from the resolved ledger path and pass it to both launch-codex-exec and _record_coder_vendor_task; set LARCH_TIMING_LEDGER to the resolved path and avoid relying on ambient IMPLEMENT_TMPDIR for ledger selection

