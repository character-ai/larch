## Proposed Design Outline

### Goals
- Single FINDING/OOS block-grammar owner in `larch/review/review_types.py`.
- All 15+ independent regex copies deleted; callers import from the owner.
- Adoption-ratchet lint bans new FINDING/OOS heading regex literals outside the owner.

### Non-goals
- Changing the wire format (heading syntax, field names, security tags).
- Touching non-Python parsers (shell scripts, fluff-analysis skill script exempt from the Python lint ratchet).
- Rewriting `_finding_dedup_key` logic; only move it to the owner.

### Approach sketch
- Extend `review_types.py` with: `parse_blocks()` (handles both FINDING and OOS IDs), `is_security_block_text()`, `count_non_security_blocks()`, `finding_dedup_key()`.
- Delete copies in `issue/oos.py`, `design/design_oos.py`, `issue/file_oos.py`, `issue/oos_disposition.py`, `review_aggregate.py`, `review_and_fix.py`, `batch_report.py`, `voting.py`, `state/dirty_tree.py`, `report/review_phase_detail.py`, `plan_review_findings.py`, `plan_review_tally.py`, `plan_review_common.py`.
- Update `lint_shared_convention_regex.py` to detect FINDING/OOS heading regex literals, with `review_types.py` on the allowlist.
- Add tests for the new grammar surface to `test_review_types.py`.

### Surfaces in scope
- `python/larch/review/review_types.py` (owner)
- `python/larch/review/review_aggregate.py`, `review_and_fix.py`, `batch_report.py`, `voting.py`, `plan_review_tally.py`, `plan_review_common.py`, `plan_review_findings.py`
- `python/larch/issue/oos.py`, `file_oos.py`, `oos_disposition.py`
- `python/larch/design/design_oos.py`
- `python/larch/state/dirty_tree.py`
- `python/larch/report/review_phase_detail.py`
- `python/larch/lint/lint_shared_convention_regex.py` (ratchet extension)
- `python/tests/review/test_review_types.py` (new tests)

### Open questions
- None.
