## Proposed Design Outline

### Goals
- Fix 10 OOS pipeline bugs: scoreboard ordering, tally eligibility, ballot error handling, security sidecar isolation, and test coverage gaps.
- Ensure security sidecar does not block non-security OOS filing or leak to design-log commits.

### Non-goals
- Refactor the OOS pipeline architecture or change public filing API contracts.
- Modify shard rebalancing logic beyond removing the stale retired node-id.
- Change voting thresholds or classification semantics beyond fixing the pre-reclassification ordering.

### Approach sketch
- Move `voter_agreement_row_from_panel` call in `review_tally.py` to after the OOS reclassification branch.
- Change `_is_vote_tally_eligible` in `oos.py` to return `False` when no Vote tally line is present.
- Remove silent error swallowing from `_ballot_block_count` in `review_core_body.py` to fail closed.
- Add `security-oos-observations.md` to the design-log publish exclusion set.
- Split `disposition_checkpoint_main` in `file_oos.py`: clear non-security disposition independently; return rc=3 when only security sidecar remains.
- Map rc=3 in `oos_filer._after_checkpoint` to `status="security_sidecar_present"` so `dispatch_ship.py` routes to `oos-pipeline`.
- Fix stale comments, update oversized-filing test scope, add sidecar sink assertions, drive real checkpoint in mixed-case test, remove retired shard entry.

### Surfaces in scope
- `python/larch/review/review_tally.py`
- `python/larch/review/review_core_body.py`
- `python/larch/issue/oos.py`
- `python/larch/design/design_log_publish_flow.py`
- `python/larch/issue/file_oos.py`
- `python/larch/issue/oos_filer.py`
- `python/tests/review/test_review_tally.py`
- `python/tests/review/test_review_aggregate.py`
- `python/tests/issue/test_oos_filer.py`
- `python/shard-assignments.json`

### Open questions
- None.
