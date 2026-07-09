## Proposed Design Outline

### Goals
- Promote G-Orch-4 and G-Obs-4 from guidelines to invariants by removing them from `ARCHITECTURAL_GUIDELINES.md` and adding I-Slot-1 and I-Outcome-1 to `ARCHITECTURAL_INVARIANTS.md`.
- Add a flush-time label check to `run_log_flush.py` that rejects terminal failure words (`stalled`, `bailed`) in pre-terminal snapshots, satisfying the I-Outcome-1 mechanical backing requirement.
- Reference existing structural tests (`test_plan_review_round.py`) as the I-Slot-1 mechanical backing.

### Non-goals
- Renumbering other G-Orch-* or G-Obs-* entries; leave gaps so historical run-log citations stay valid.
- Adding new enforcement code for the I-Slot-1 prune-ledger path; existing tests already cover it.
- Changing the enforcement scope for any other guideline or invariant.

### Approach sketch
- Remove G-Orch-4 and G-Obs-4 entries from `ARCHITECTURAL_GUIDELINES.md` (section gaps left, headings gone).
- Add I-Slot-1 under a new `## Panel integrity` section in `ARCHITECTURAL_INVARIANTS.md`, referencing `reviewer-prune-ledger.tsv`, `*-slots.ndjson`, and existing `test_plan_review_round.py` tests.
- Add I-Outcome-1 under the existing `## Run-log integrity` section, referencing the new flush-time label check.
- Add `_check_preterminal_outcome_label()` to `run_log_flush.py` and call it before the outcome label is committed; raise `ShipError` on forbidden terminal words.
- Add regression tests in `test_run_log_flush.py` covering the guard on pre-terminal snapshots.

### Surfaces in scope
- `ARCHITECTURAL_GUIDELINES.md`
- `ARCHITECTURAL_INVARIANTS.md`
- `python/larch/report/run_log_flush.py`
- `python/tests/report/test_run_log_flush.py`

### Open questions
- None.
