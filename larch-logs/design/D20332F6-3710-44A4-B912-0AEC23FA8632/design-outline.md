## Proposed Design Outline

### Goals
- Add one stdlib-only module `python/larch_io.py` for KV read/write, atomic write, and text read/write/append.
- Repoint every behavioral duplicate of these helpers across `python/` to the shared module; delete the local copies.
- Keep behavior identical at every call site (the "behavior unchanged" parity gate).

### Non-goals
- No change to on-disk wire formats (`KEY=value` stdout grammar, `.sh` env-file format). Refactor parsing, not format.
- Do not move `normalize_reviewer_label` (single definition, reviewer-domain; stays in `review_pipeline.py`).
- No behavior changes, no new features; pure dedup refactor.

### Approach sketch
- Define pure functions in `larch_io.py`: `parse_kv`, `read_kv`, `write_kv`/`write_kvs`, `atomic_write`, `read_text`, `write_text`, `append_text`.
- Cover divergent semantics via parameters so no call-site changes: KV file read first-vs-last match; dict parse first-vs-last wins; atomic-write `mode`/`create_parent`.
- Classify each candidate before repointing. Collapse only true behavioral duplicates. Adapt or skip variants that differ (e.g. float-valued or single-key stdout parsers).
- Repoint file-by-file, deleting each local helper after its callers move. Add `python/test_larch_io.py`; existing `make py-test` is the regression guard.

### Surfaces in scope
- New: `python/larch_io.py`, `python/test_larch_io.py`.
- Repoint (representative): `review_pipeline.py`, `review_tally.py`, `review_aggregate.py`, `review_and_fix.py`, `run_logs.py`, `session_env.py`, `tokens.py`, `design_lifecycle.py`, plus the wider `_parse_kv`/`_atomic_write`/`_write_text_atomic` family across `python/`.

### Open questions
- Lift the existing `stall_recovery.read_kv` / `session_env` KV writer as the canonical implementations, vs. write fresh in `larch_io`. (Lean: lift the best existing one.)
- Treat near-duplicate-but-not-identical parsers (float-valued `report_tokens_cost`, single-key stdout getters) as in-scope adapters or leave them. (Resolve during plan drafting.)
