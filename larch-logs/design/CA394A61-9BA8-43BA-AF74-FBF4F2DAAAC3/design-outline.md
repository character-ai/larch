## Proposed Design Outline

### Goals
- Persist a committed, content-free size fact each time a real checks-repair-loop digest is generated, so a real sample population accrues in `larch-logs/`.
- Add a `token measure-checks-digest-savings` aggregator that reports insufficient-data until >=5 samples exist, then computes the realized digest-vs-full-log delta.
- Leave the go/no-go decision and any validator-loop extension for a later run of the aggregator once real data exists.

### Non-goals
- No synthetic/local benchmark to close out #6164's acceptance criteria immediately.
- No extension of the digest pattern to `skills/design/references/validator-failure.md` in this change — gated on a future positive measurement.
- Not closing issue #6164 in this PR — its acceptance criteria stay open pending real data.

### Approach sketch
- Instrument the single shared digest-generation point in `checks_run_relevant.py` (`_write_failure_digest_from_redacted`) to also best-effort-append one row to a new dedicated per-run TSV, mirroring the existing `append_panel_prompt_size` / `panel-prompt-sizes.tsv` pattern (locked append, `_estimate_tokens_for_bytes`, try/except-non-blocking) — covers `/implement` and `/review` for free since both consume this helper.
- Add `python/cli.py token measure-checks-digest-savings`, mirroring `measure_panel_cost`: glob committed rows under `larch-logs/**/`, aggregate, and write a stamped report under `larch-logs/measure-checks-digest-savings/`.

### Surfaces in scope
- `python/larch/implement/checks_run_relevant.py`
- `python/larch/report/tokens.py` (or a small sibling module) plus `python/larch/cli.py` registry
- `docs/run-logs.md`, `docs/run-log-batches.md`
- Tests for the writer and aggregator

### Open questions
- None.
