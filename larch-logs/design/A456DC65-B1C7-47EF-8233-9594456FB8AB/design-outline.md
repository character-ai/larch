## Proposed Design Outline

### Goals
- Port 20 token/timing/cost bash scripts to two Python modules (`tokens.py` extension + new `timing.py`).
- Register `token` and `timing` CLI domains in `cli.py`; cut all consumers to `python3 cli.py <domain> <verb>`.
- Delete retired bash scripts, `.md` siblings, and bash harnesses; confirm `make lint-retired-scripts` clean.

### Non-goals
- Byte-for-byte output parity with `token-report.sh`/`timing-report.sh` (functionally equivalent is sufficient).
- Changes to pricing rates in `report_tokens_cost.py`.
- Adding new token/timing features beyond replicating existing script behavior.

### Approach sketch
- Extend `python/tokens.py`: add `TokenLedger`, `TokenTally`, `CostLine`, `token_report()`, and measure/utility functions.
- Create `python/timing.py`: `TimingLedger`, `TimingReport`, `harness_mark()`, `telemetry_mark()`, constants.
- Add both domains to `cli.py`; wire all verbs to module entry points.
- Cut over every consumer in one commit: `scripts/`, `skills/design/SKILL.md`, `skills/implement/SKILL.md`, `Makefile`, `checks.py`, `run_logs.py`, docs.
- Append 20+ deleted paths to `python/migrated-scripts.tsv`; run `make lint + py-lint + py-test`.

### Surfaces in scope
- `python/tokens.py`, `python/timing.py`, `python/test_tokens.py`, `python/test_timing.py`
- `python/cli.py`, `python/checks.py`, `python/run_logs.py`, `python/migrated-scripts.tsv`
- `scripts/implement-bootstrap.sh`, `scripts/launch-*.sh`, `scripts/render-run-summary.sh`, `scripts/refresh-run-logs.sh`, `scripts/design-pause-save.sh`
- `skills/design/SKILL.md`, `skills/implement/SKILL.md`
- `Makefile`, `docs/python-migration.md`, `docs/run-logs.md`, `docs/workflow-lifecycle.md`, `scripts/*.md` stale refs
- All 20 retired bash scripts + `.md` siblings + bash harnesses (DELETED)

### Open questions
- None.
