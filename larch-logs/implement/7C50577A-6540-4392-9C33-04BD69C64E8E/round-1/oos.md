### FINDING_1: [OUT_OF_SCOPE] Duplicate cached-version discovery logic
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `list_cached_versions_by_mtime` still duplicates numeric cached-version directory discovery logic; only ordering differs from the removed semver helper.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### FINDING_2: [OUT_OF_SCOPE] Parallel version ordering models remain
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `upgrade-larch.sh` still uses mtime ordering for prune eviction while other helpers depend on semver ordering, leaving two version-ordering models in one script.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_3: [OUT_OF_SCOPE] Prune-failure cap-overflow path lacks coverage
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-test-coverage-output.txt
- **Severity**: latent
- **Concern**: The cap-overflow warning is covered for all-pinned stalls, but not for cases where removable entries remain above the cache cap because removals fail via `RM_FAIL_VERSION` / `PRUNE_FAILED_VERSIONS`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-test-coverage-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_6: [OUT_OF_SCOPE] Environment cleanup concern was resolved
- **Reviewer(s)**: dyn-test-coverage-output.txt
- **Severity**: nit
- **Concern**: Reviewer notes that relevant environment variables are cleared or overwritten before the new test block, so no leak affects the case under current ordering.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-test-coverage-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_7: [OUT_OF_SCOPE] `29.1.29` omission is intentional
- **Reviewer(s)**: dyn-test-coverage-output.txt
- **Severity**: nit
- **Concern**: Reviewer notes that `29.1.29` is intentionally absent from the kept-version loop because it is not installed or seeded as a cache directory.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-test-coverage-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_8: [OUT_OF_SCOPE] Pinning wiring matches scenario
- **Reviewer(s)**: dyn-test-coverage-output.txt
- **Severity**: nit
- **Concern**: Reviewer notes that the session pins, executing-root pin, and latest-stable protection correctly model the intended all-pinned cap-overflow scenario.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-test-coverage-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_9: [OUT_OF_SCOPE] Harness sibling documentation not updated
- **Reviewer(s)**: dyn-test-coverage-output.txt
- **Severity**: nit
- **Concern**: `skills/upgrade-larch/scripts/test-upgrade-larch-prune.md` was not updated to mention the new `all-pinned-cap-overflow-warns` harness case.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-test-coverage-output.txt: Address the concern above.

Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

