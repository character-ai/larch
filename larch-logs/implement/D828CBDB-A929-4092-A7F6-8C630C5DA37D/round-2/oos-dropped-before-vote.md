### OOS_1: [OUT_OF_SCOPE] Gate C reentry pool reset lacks regression test
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: The Gate C reentry pool reset has no automated regression test, so stale pool state could re-trigger promotion after review re-entry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Gate C reentry pool reset has no automated regression test Stale pool could re-trigger promotion after review re-entry Add shell or lifecycle test asserting oos-aggregate-pool.md removal on --reentry

### OOS_2: [OUT_OF_SCOPE] Dead annotate-skipped-empty-stdout branch appears unreachable after status rename
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: The `annotate-skipped-empty-stdout` branch appears unreachable after the annotate status rename, so the branch is dead code unless the status vocabulary is aligned again.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: annotate-skipped-empty-stdout branch appears unreachable after annotate status rename Dead branch plus misleading test maintenance Remove dead branch or align status vocabulary with design_oos.py

### OOS_3: [OUT_OF_SCOPE] Once-only retry sentinel lacks end-to-end harness
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: The once-only retry sentinel is prompt-orchestrator owned without an end-to-end harness, so double retry or silent Step 5b advance may only surface in live `/design` runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Once-only retry sentinel is prompt-orchestrator owned without end-to-end harness Double retry or silent Step 5b advance may only surface in live /design runs Add integration coverage when skill orchestration is testable; until then strengthen step5b/annotate unit tests

