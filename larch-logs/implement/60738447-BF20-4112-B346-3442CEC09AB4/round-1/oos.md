### FINDING_3: [OUT_OF_SCOPE] Accepted OOS scoreboard assertions are missing in review-tally tests
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: The review-tally path in `python/tests/review/test_review_tally.py` does not assert that accepted OOS is rendered in the Voter Agreement Scoreboard in `voting-tally.md`, so the classification TSV can say accepted while the scoreboard section stays stale.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted

### FINDING_4: [OUT_OF_SCOPE] step8_oos_checkpoint can stall on rc=3
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: `python/larch/implement/dispatch_ship.py` can leave `step8_oos_checkpoint` stalled on checkpoint `rc=3` after an uncleared sidecar from `oos-pipeline`, which causes a stall rather than a retry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### FINDING_5: [OUT_OF_SCOPE] checkpoint only checks the top-level sidecar path
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: `python/larch/issue/file_oos.py` only inspects the top-level sidecar path, so nested design-export copies would not gate on `rc=3`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### FINDING_6: [OUT_OF_SCOPE] agreement rows ignore neutral_rescued
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: `python/larch/review/review_tally.py` builds agreement rows without `neutral_rescued`, which can make the scoreboard disagree with the final OOS classification on rescue paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted

### FINDING_7: [OUT_OF_SCOPE] Parse-error logging should not depend on an absent tmpdir
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: nit
- **Concern**: `python/larch/issue/file_oos.py` writes parse-error logging into an unchecked `--implement-tmpdir`, so malformed args plus a missing tmpdir can crash the checkpoint instead of failing closed with `rc=2`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Address the concern above.


Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted

### FINDING_9: [OUT_OF_SCOPE] rejected-counting needs regression coverage for ### subheadings
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: `python/larch/issue/file_oos.py` now treats `###` subheadings as in-section in `_count_rejected_from_ndjson`, but there is no targeted regression test for rejected blocks that contain nested headings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### FINDING_10: [OUT_OF_SCOPE] rc=3 bash path is outside the CI harness matrix
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: `skills/implement/scripts/test-oos-disposition-gate.sh` adds an updated bash `rc=3` case that is not exercised by the test-harnesses CI matrix, so the bash contract can diverge from enforced CI behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

