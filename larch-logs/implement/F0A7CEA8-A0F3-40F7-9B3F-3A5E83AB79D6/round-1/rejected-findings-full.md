### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: launch_calls does not prove vendor waterfall tier sequence
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: In python/test_ci_monitor.py:1238-1292, `assert launch_calls` is weaker than plan language that the vendor launcher ran through the waterfall: a stub that skips the waterfall but still returns STALLED could pass if any unrelated launch occurred.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Assert tier sequence or minimum launch count aligned with run_waterfall / _available_tiers().


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: Duplicate vendor push-failure stub maps across monitor and evaluate tests
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `test_evaluate_failure_vendor_only_push_failed_stalls` and `test_monitor_push_failed_stalls` (python/test_ci_monitor.py:973-1027 and 1238-1292) duplicate large response/stub maps; updating one test only can leave the other green while monitor and evaluate paths diverge.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract _vendor_only_push_failure_responses(run_id=...) shared by both tests.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: Document push-failure dirty-tree semantics in ci_monitor comment
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The new comment at python/ci_monitor.py:1014-1024 does not state that push-failure returns without `_rollback()`, leaving an unpushed local commit while the outer loop re-enters the full fix waterfall from a dirty tree—unlike bash `CI_FIX_REBASE_PENDING` push-only retry. Phase 7 readers may assume idempotent clean re-fix.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add one comment line: local commit retained on push failure; outer retries re-enter waterfall from dirty state; contrast with bash CI_FIX_REBASE_PENDING push-only retry.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: Monitor test does not exercise post-commit HEAD advance on push failure
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: In python/test_ci_monitor.py:1275-1290, `git rev-parse HEAD` stays frozen at `baseline_head` after a mocked successful commit while push fails. Production may see head-changed or duplicate-commit on outer retry; the test would still pass while real recovery diverges.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Advance post-commit rev-parse stub to new SHA with push rc=1 or add test covering unpushed-commit outer-retry semantics.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

