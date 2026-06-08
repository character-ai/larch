## Proposed Design Outline

### Goals
- One argparse dispatcher `python/cli.py`: `<domain> <verb>` grammar, lazy domain imports, fd-3 lib-quiet KV contract, exit-code passthrough.
- Land `docs/python-migration.md`: per-domain recipe + decision log (no shims, hard cutover, hooks stay bash, flat layout, stdlib-only py3.11+).
- Retired-scripts manifest + Python lint (a cli.py subcommand) that fails CI on stale references to retired paths.

### Non-goals
- No new domain ports (F2+ own those); no hooks changes.
- No `scripts/ship-pr.sh` / `LARCH_SHIP_PR_IMPL` retirement (E1 owns it); the bash opt-in path stays.
- No .sh shims; no dual-path selectors for adopted domains.

### Approach sketch
- cli.py holds a domain registry; only the requested domain's module imports (startup stays cheap).
- Adopt `ship` + `report-tokens` as the first real domains, delegating to existing modules; cut all consumers over to direct cli.py calls.
- Retire `run-analysis.sh` + `test-run-analysis-quiet.sh` (+ .md siblings); port quiet-restore semantics to pytest; seed the manifest with these first entries.
- Lint scans all git-tracked files minus exclusions (CHANGELOG.md, larch-logs/, the manifest itself) for retired-path references; `make lint` calls cli.py directly.

### Surfaces in scope
- `python/` (cli.py, lint module, colocated tests), `docs/python-migration.md`, Makefile, `.github/workflows/ci.yaml`.
- `skills/implement/` (SKILL.md + references), `skills/report-tokens/`, `scripts/relevant-checks.sh`, `scripts/test-implement-structure.sh`, AGENTS.md, `docs/linting.md`, `python/README.md`.

### Open questions
- None.
