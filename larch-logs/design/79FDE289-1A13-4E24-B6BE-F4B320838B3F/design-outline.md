## Proposed Design Outline

### Goals
- Create `python/tests/support/review_wire.py` with canonical factories for finding blocks, rejected blocks, vote lines, ballot snippets, and slot-manifest NDJSON.
- Migrate the review cluster test files to import and use these factories, so a single finding-block or vote-line grammar edit propagates everywhere.

### Non-goals
- No changes to production code (`python/larch/`).
- No migration of test files outside the listed review cluster.
- No new test logic; factories replicate existing inline patterns, not extend them.

### Approach sketch
- Define `make_finding_block`, `make_rejected_block`, `ballot_snippet`, `vote_lines`, `slot_manifest_ndjson`, and `plan_review_slot_line` in `review_wire.py`.
- Replace local `_make_rejected_block` / `_make_finding_only_rejected_block` in `test_plan_review.py` with imports from `review_wire`.
- Migrate `test_review_tally.py` and `test_voting.py` inline finding-block and vote-line literals to shared factories.
- Adopt `slot_manifest_ndjson` / `plan_review_slot_line` in MAY_UPDATE files (aggregate, panel, round, phase-detail, test_support.py) where the pattern is a clear fit.

### Surfaces in scope
- `python/tests/support/review_wire.py` (new)
- `python/tests/review/test_plan_review.py`
- `python/tests/review/test_review_tally.py`
- `python/tests/review/test_voting.py`
- `python/tests/review/test_review_aggregate.py` (MAY_UPDATE)
- `python/tests/review/test_plan_review_panel.py` (MAY_UPDATE)
- `python/tests/review/test_plan_review_round.py` (MAY_UPDATE)
- `python/tests/report/test_review_phase_detail.py` (MAY_UPDATE)
- `python/test_support.py` (MAY_UPDATE, slot_manifest reuse in make_zero_findings_plan_review_fake_cli)

### Open questions
- None.
