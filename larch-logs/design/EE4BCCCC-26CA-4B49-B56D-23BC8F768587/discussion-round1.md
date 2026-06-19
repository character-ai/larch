## Decision 1: E1-flagged scripts (ci-failed-jobs.sh, ci-rerun-failed.sh)
- **Question**: Delete in this slice, or defer as possible ship-pr-only leftovers?
- **Resolution**: Delete both. Python parity verified — `ci-failed-jobs.sh`→`ci failed-jobs` and `ci-rerun-failed.sh`→`ci rerun-failed` are registered in `cli.py`. Repoint any live consumers, run their retargeted test harnesses once as the parity gate, then delete the `.sh` + `.md` + test siblings like the other 14.
- **Source**: user (grounded by codebase parity check)

## Decision 2: Reference-cleanup breadth
- **Question**: Clean only linter-flagged references, or all stale mentions including bare-basename prose?
- **Resolution**: Rewrite all stale mentions. Update bare-basename prose in docs (`SECURITY.md`, `skills/design/references/flags.md`) and `python/*.py` comments/docstrings to the `cli.py` verb, in addition to the linter-blocking full-path / same-dir references. Accept a wider diff to avoid stale-prose debt (the #1 OOS source).
- **Source**: user

## Decision 3: Scope boundaries (codebase-derived)
- **Question**: What is in-scope vs out-of-scope for G13?
- **Resolution**: In-scope — repoint all consumers of the 16 listed scripts to `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" <domain> <verb>`; delete the 16 `.sh` plus their `.md` and `test-*.sh`/`test-*.md` harness siblings; append deleted paths to `python/migrated-scripts.tsv` with `#4642`; `make lint-retired-scripts` clean. Out-of-scope — re-porting (Python ports already exist and execute no `.sh`), Claude Code hooks (stay bash per decision log), `larch-logs/` (linter-excluded, historical), `CHANGELOG.md` (linter-excluded).
- **Source**: codebase (docs/python-migration.md recipe + issue DoD)

## Decision 4: Hard constraints (must not break)
- **Question**: What existing behavior must be preserved?
- **Resolution**: `cli.py` verb parity must hold per script before its `.sh` is deleted (recipe step 5 = run retargeted `test-*.sh` harness once as the parity gate). `ship pr` and CI workflows must keep working after repointing. No shims/forwarding stubs (hard cutover). Bash callers derive plugin root from their local script dir first, falling back to `${CLAUDE_PLUGIN_ROOT}`. Do NOT write retired-path literals in test fixtures — build paths at runtime.
- **Source**: codebase (docs/python-migration.md decision log + recipe)
