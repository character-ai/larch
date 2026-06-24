### OOS_6: [OUT_OF_SCOPE] Process-global ground-truth caches lack mtime invalidation
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-dyn-oos-verdicts-output.txt, dyn-dyn-voter-prep-output.txt
- **Severity**: nit
- **Concern**: Process-global `_GROUND_TRUTH_ROW_CACHE` / `_GROUND_TRUTH_FILED_CACHE` and `@functools.lru_cache` prose readers keyed only by `Path` have no mtime/size invalidation. Repeated `analyze-issues` or `ground_truth_voter_calibration` calls in one Python process after log edits can return stale rows, prose joins, or OOS fate scoring.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Key caches by `(path, mtime, size)` or disable caching for interactive reruns.
  - From dyn-dyn-oos-verdicts-output.txt: Key caches by `(path, mtime_ns, size)` or drop cross-call caching for diagnostic code paths.
  - From dyn-dyn-voter-prep-output.txt: Key caches by `(path, mtime_ns, size)` or drop cross-call caching for diagnostic code paths.


### OOS_7: [OUT_OF_SCOPE] timestamp_degraded counter increments per evidence candidate
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `timestamp_degraded` increments per evidence candidate rather than per source row. One row scanning many issues inflates the Timestamp-degraded corpus bullet without changing outcomes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Increment once per source row when any candidate is timestamp-degraded.


### OOS_8: [OUT_OF_SCOPE] make test-analyze docs over-claim fixture coverage
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `docs/linting.md` claims isolated fixture coverage for ground-truth categories that are only exercised inside one consolidated mega-test. Maintainers may assume gc-slimmed, enrichment-degraded, or round-ordering regressions have dedicated failing tests when they do not.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Split listed categories into named tests or narrow the linting.md coverage prose.
  - From cursor-specialist-testing-output.txt: Align docs with actual fixtures or add the missing tests before documenting them.


### OOS_9: [OUT_OF_SCOPE] >5000 row cap disables filed-OOS evidence for large corpora
- **Reviewer(s)**: dyn-dyn-oos-verdicts-output.txt
- **Severity**: important
- **Concern**: The `>5000` row cap still disables `iter_filed_oos_records` for ground-truth OOS fate scoring. Large corpora can render per-voter tables without accepted-OOS docked evidence while appearing structurally complete.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-oos-verdicts-output.txt: Address the concern above.


### OOS_10: [OUT_OF_SCOPE] Ground-truth tests lack OOS verdict/fate boundary pins
- **Reviewer(s)**: dyn-dyn-oos-verdicts-output.txt
- **Severity**: important
- **Concern**: Ground-truth tests cover one happy-path OOS dock but do not pin rejected-OOS-panel non-decisive behavior, TSV/tally disagreement, weak-prose plus accepted TSV, or multi-round filed-record collision. Regressions on the OOS verdict/fate boundary can ship without a targeted failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-oos-verdicts-output.txt: Address the concern above.


