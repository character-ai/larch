## Proposed Design Outline

### Goals
- Repoint every consumer of the 16 ci/pr/merge/push/gh bash scripts to `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" <domain> <verb>`.
- Delete the 16 `.sh` plus their `.md` and `test-*` harness siblings; append deleted paths to `python/migrated-scripts.tsv` with `#4642`.
- Land `make lint-retired-scripts` clean (no tracked file references a retired path).

### Non-goals
- No re-porting; the Python modules already exist and execute no `.sh`.
- No changes to Claude Code hooks (stay bash); no edits to `larch-logs/` or `CHANGELOG.md` (linter-excluded).
- No shims or `.sh` forwarding stubs (hard cutover).

### Approach sketch
- Build the per-script verb map (`merge-pr.sh`→`merge pr`, `create-branch.sh`→`pr create-branch`, `ci-*`→`ci <verb>`, `gh-*`/`resolve-repo`→`gh <verb>`) and confirm parity per verb.
- Repoint consumers across skill `.md` fences, `Makefile`, `.github/` CI, and bash callers; rewrite name-mentions in `python/*.py` and docs prose (Round 1 Decision 2).
- Run each retargeted `test-*.sh` once as the parity gate (recipe step 5), then delete the script + siblings (steps 6-7).
- Append to `migrated-scripts.tsv`; verify with `make lint-retired-scripts` and `make lint`.

### Surfaces in scope
- `scripts/`: the 16 `.sh` + their `.md` + `test-*` siblings; `python/migrated-scripts.tsv`.
- Consumers: `skills/**/*.md`, `Makefile`, `.github/workflows/`, `python/*.py` references, `SECURITY.md`, `skills/design/references/flags.md`.

### Open questions
- None.
