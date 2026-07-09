### FINDING_4: [OUT_OF_SCOPE] direct gh.pr_create remains ungated
- **Reviewer(s)**: codex-specialist-correctness, cursor-specialist-edge-cases, dyn-dyn-scope-gate
- **Severity**: major
- **Concern**: `gh.pr_create` remains an unguarded low-level PR mutation helper, so direct callers can create a PR without scope-disposition validation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-scope-gate: Address the concern above.


Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_5: [OUT_OF_SCOPE] push_branch should not rely only on the earlier gate
- **Reviewer(s)**: cursor-specialist-edge-cases, dyn-dyn-scope-gate
- **Severity**: minor
- **Concern**: `push.push_branch` and `cli.py push branch` do not re-run the PR mutation gate after the initial `ensure_pr` / ship pre-driver check, so later pushes can proceed without revalidating stale scope-disposition state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-scope-gate: Address the concern above.


Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_6: [OUT_OF_SCOPE] bail-rescope records can be skipped after the early return
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: `validate_disposition_for_ship` returns ok when `disposition_required` is false before checking bail-rescope records, so a matching-fingerprint bail-rescope record could be skipped if recomputed coverage no longer requires disposition.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

### FINDING_11: [OUT_OF_SCOPE] new tests are missing from the shard assignment map
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: New tests are not assigned in the shard map.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_12: [OUT_OF_SCOPE] malformed plan-coverage.json lacks a focused gate test
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: There is no unit test for malformed `plan-coverage.json` on a gate-relevant tmpdir, so malformed coverage handling is only inferred from other recompute-failure tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_13: [OUT_OF_SCOPE] nested manifest resolution lacks coverage
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: `codex-step2-out/manifest.json` resolution is untested, so the alternate manifest location could regress without a targeted test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.
Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=false

