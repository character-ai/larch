### OOS_1: atomic baseline writes
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: Baseline `--write` uses direct `write_text` instead of atomic larch.io replacement. A crash during `--write` could leave `suppression-reason-baseline.json` partially written; not a false pass/fail in the scanner itself.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### OOS_2: duplicate suppression rows churn baselines
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: Occurrence-based baseline keys omit line numbers, so deleting an earlier duplicate suppression renumbers later rows and triggers stale-baseline failures until regen.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Document the workflow prominently or add an optional line-number disambiguator if churn becomes painful


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### OOS_3: `--initial-reason` can widen existing baselines
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: When `--write --initial-reason` is combined with an existing baseline, it can seed new rows without the fail-closed path used for routine regen.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Ignore `--initial-reason` when the baseline file already exists, or require an explicit `--allow-bootstrap-reasons` flag


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### OOS_4: empty trailing `pylint` reason lacks coverage
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: The suite does not parameterize the empty trailing `# pylint: disable=foo #` edge case, so that low-risk post-hoc coverage gap could regress unnoticed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add parametrized case only if desired; not plan-required.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

### OOS_5: new scan may slow `py-lint-checks-fast`
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: The new lint adds another full-tree scan to `py-lint-checks-fast`, which raises CI latency even though no timeout failure was demonstrated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Monitor shard-1 timing; optimize only if regressions appear.
Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

