## Proposed Design Outline

### Goals
- Report true multi-round results in `code-review-tally.json`: `rounds` = committed `round-*` count; `accepted_count` / `rejected_count` = cumulative across rounds.
- Stop the tally write from silently freezing at round 1.
- Document the cumulative semantics as a shared contract.

### Non-goals
- Backfilling already-committed historical tallies.
- Changing tally consumers (`audit-runs`, `/fluff-analysis`, token/cost summaries).
- A separate standalone `/review` test (the shared-writer fix covers it).
- Touching the `review-findings-full.jsonl` path (already correct).

### Approach sketch
- Root cause: `voting write-tally` calls `_die` on code-review body header-validation failure before writing; the body is discarded for code-review, so the gate only harms.
- Make code-review tally-body validation non-fatal: warn, then write the record. Keep the existing cumulative count derivation and the explicit round count.
- Leave the plan-review tally path untouched (it stores and uses its body).
- Add a 2+ round regression test: written tally `rounds` == round-dir count and counts == cumulative, even when a body line trips the old gate.

### Surfaces in scope
- `python/voting.py` — `write_tally_main` code-review validation gate.
- `docs/run-logs.md` — cumulative-semantics contract.
- `python/test_voting.py`, `python/test_review_and_fix.py` — regression coverage.

### Open questions
- None.
