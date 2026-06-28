### OOS_1: [OUT_OF_SCOPE] Ground-truth cache staleness in long-lived processes
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: Process-wide `_GROUND_TRUTH_ROW_CACHE`, `_GROUND_TRUTH_FILED_CACHE`, and `functools.lru_cache` layers in `python/larch/issue/_ground_truth.py:149-150,425-446` key on path strings and file content snapshots, not log mutations. A long-lived Python process that re-runs calibration against an updated `log_root` without calling `.clear()` (as tests do) can reuse stale row scans or filed-OOS records.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: None required for this split; if freshness matters in interactive sessions, add explicit cache invalidation or document the long-lived-process contract.

### OOS_2: [OUT_OF_SCOPE] Remaining large module surfaces after split
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: The split removes the 3,546-line god-module, but `_oos.py` (~1,085 LOC) and `_ground_truth.py` (~1,575 LOC) remain large merge/conflict surfaces. Further subdivision may be warranted by the umbrella capstone (13/14).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Track as follow-on split work outside this PR's scope.

### OOS_3: [OUT_OF_SCOPE] Subprocess baseline rows not relocated with gh issue view moves
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: Two `gh issue view` subprocess calls moved from `analyze_issues.py` to `_oos.py` (`python/subprocess-via-runner-baseline.json:1074-1099` vs `python/larch/issue/_oos.py:784,855`). Baseline rows were not relocated; inline `# lint-subprocess-via-runner: ok` pragmas carry the exemption.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: On next baseline refresh, add `_oos.py` rows or consolidate grandfathered entries so file moves do not depend solely on per-line pragmas.

### OOS_4: [OUT_OF_SCOPE] Missing import-contract tests for downstream skill consumers
- **Reviewer(s)**: dyn-dyn-module-split
- **Severity**: latent
- **Concern**: The 90-test harness in `python/test_analyze_issues.py` exercises `analyze_issues.*` re-exports thoroughly but does not import-check downstream skill consumers like `voter-calibration.py`. A small import-contract test (or running `make test-voter-calibration` in CI for splits touching `analyze_issues`) would catch missing re-exports before merge.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-module-split: A small import-contract test (or running `make test-voter-calibration` in CI for splits touching `analyze_issues`) would catch missing re-exports before merge.
