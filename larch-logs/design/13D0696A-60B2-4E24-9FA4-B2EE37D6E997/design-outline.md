## Proposed Design Outline

### Goals
- Correct Codex and Cursor rate constants (Codex ~11x under, Cursor ~1.5x over).
- Consolidate all pricing code and constants into a single Python module (`report_tokens_cost.py`); remove all duplicates.
- Add a model-basis drift guard so rate-table and configured models cannot diverge silently.

### Non-goals
- Per-record model-keyed pricing (each ledger row priced by its specific model).
- Distinct raw labels for aggregator/judge Codex calls.
- Data migration of committed run logs.

### Approach sketch
- Update constants in `python/report_tokens_cost.py`; add `VENDOR_RATE_TABLE` keyed by `(vendor, model)` and `DEFAULT_VENDOR_MODEL` map.
- Derive blended fallback rates from per-bucket constants + documented fleet mix (7% input, 92% cache-read, 1% output).
- Delete `env_rate()` and `display_rates()` from `python/report_tokens_models.py`; update its callers.
- Add `TOKEN_RECORD` emit to `launch-codex-drafter.sh`; ingest in `design-step2b-drafter.sh`.
- Add model-basis consistency test (Python or shell) comparing `DEFAULT_VENDOR_MODEL` to `agent-model-args.sh` defaults.

### Surfaces in scope
- `python/report_tokens_cost.py` — single pricing authority
- `python/report_tokens_models.py` — remove duplicate functions
- `scripts/launch-codex-drafter.sh` — emit TOKEN_RECORD for drafter sidecar
- `skills/design/scripts/design-step2b-drafter.sh` — ingest drafter token-record
- `docs/configuration-and-permissions.md` — update "Per-vendor rates" section
- `python/test_report_tokens_cost.py`, `python/test_report_tokens_models.py` — update/convert tests
- `python/fixtures/report_tokens_*.md`, `scripts/test-render-run-summary*.sh` — update dollar fixtures

### Open questions
- None.
