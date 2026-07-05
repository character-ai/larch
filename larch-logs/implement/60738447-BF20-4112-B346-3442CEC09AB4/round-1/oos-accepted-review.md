### OOS_1: [OUT_OF_SCOPE] Accepted OOS scoreboard assertions are missing in review-tally tests
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: The review-tally path in `python/tests/review/test_review_tally.py` does not assert that accepted OOS is rendered in the Voter Agreement Scoreboard in `voting-tally.md`, so the classification TSV can say accepted while the scoreboard section stays stale.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


### OOS_2: [OUT_OF_SCOPE] agreement rows ignore neutral_rescued
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: `python/larch/review/review_tally.py` builds agreement rows without `neutral_rescued`, which can make the scoreboard disagree with the final OOS classification on rescue paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


### OOS_3: [OUT_OF_SCOPE] Parse-error logging should not depend on an absent tmpdir
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: nit
- **Concern**: `python/larch/issue/file_oos.py` writes parse-error logging into an unchecked `--implement-tmpdir`, so malformed args plus a missing tmpdir can crash the checkpoint instead of failing closed with `rc=2`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Address the concern above.


