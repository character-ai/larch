# Discussion Round 1 — Resolved Decisions

## Decision 1: Initial cli.py domains
- **Question**: What should `python/cli.py` register as its initial domain(s) in F1?
- **Resolution**: Adopt `ship` and `report-tokens` as real domains now (cut over their consumers), plus the new retired-scripts lint subcommand.
- **Source**: user

## Decision 2: Migrated-scripts lint implementation
- **Question**: Python module exposed as a cli.py subcommand, or conventional bash `scripts/lint-*.sh`?
- **Resolution**: Python via cli.py. New `python/` module; Makefile target calls `python3 python/cli.py` directly. Dogfoods the direct-call convention.
- **Source**: user

## Decision 3: Lint scan scope
- **Question**: Scan only the issue's listed surfaces, or all tracked files?
- **Resolution**: All git-tracked text files, excluding CHANGELOG.md, larch-logs/ (committed run logs), the manifest itself, and test fixtures.
- **Source**: user

## Decision 4: run-analysis.sh wrapper fate
- **Question**: Retire `skills/report-tokens/scripts/run-analysis.sh` + `test-run-analysis-quiet.sh` (+ .md siblings) in F1?
- **Resolution**: Retire fully. Delete wrapper + harness + .md siblings, port quiet-restore harness semantics to pytest, seed the migrated-scripts manifest with these first real entries.
- **Source**: user

## Decision 5: LARCH_SHIP_PR_IMPL legacy bash path
- **Question**: Does the ship cutover touch the `LARCH_SHIP_PR_IMPL=bash` legacy path?
- **Resolution**: No. E1 (#3690) owns retiring `scripts/ship-pr.sh` and the selector. F1 repoints only the default Python branch invocation (`python3 .../python/ship.py` → `python3 .../python/cli.py ship ...`) in skills/implement surfaces.
- **Source**: codebase

## Decision 6: CI Python availability for the new lint
- **Question**: Can a Python-based lint run in CI lint jobs?
- **Resolution**: Yes. Both lint jobs in `.github/workflows/ci.yaml` already run `actions/setup-python@v6` with python-version 3.11; test-harness shards do too.
- **Source**: codebase

## Hard constraints (from issue + umbrella #3692)
- stdlib-only, Python >= 3.11; flat python/ layout.
- No .sh shims; hard cutover (no new LARCH_*_IMPL selectors).
- Hooks stay bash (out of scope).
- fd-3 lib-quiet KV contract preserved via `logging_util.quiet_init()` / `contract_stream()`.
- `make py-lint` / `make py-test` must stay green; manifest lint wired into `make lint`.
