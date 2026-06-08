## Proposed Design Outline

### Goals
- Consolidate ~40 standalone git/gh/CI helper scripts into the existing `python/{git,gh,pr,push,merge,ci_monitor}.py` surfaces plus a CLI-facing `ci` namespace; expose `cli.py` verbs.
- Hard-cutover every live consumer (skills `.md`, docs, `Makefile`, CI, bash) to `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" <domain> <verb>`; no shims, no `LARCH_*_IMPL` selector.
- Port white-box harness semantics to colocated pytest; delete each bash + its `.sh`/`.md`/`test-*.sh` siblings; append `migrated-scripts.tsv`; `make lint-retired-scripts` + `lint` + `py-lint` + `py-test` green.

### Non-goals
- Touching `scripts/ship-pr.sh` or its inlined copies (E1 retires it later).
- Converting Claude Code hooks to Python (hooks stay bash; none reference these scripts).
- Re-porting functions already present in the ship-pr-era Python modules — reuse them, add only the gaps.

### Approach sketch
- Map each script to its domain module: git primitives → `git.py`; create-branch/create-pr/pr-body → `pr.py`; push/force-push/rebase-push → `push.py`; merge → `merge.py`; gh/run-logs/remote → `gh.py`; `ci-*` → `ci_monitor.py` + new `ci` CLI namespace.
- Audit each module for missing functions; add importable functions + register `(domain, verb)` rows in `cli.py` `_REGISTRY`; fd-3 KV contract via `quiet_init`/`emit_kv`.
- Fold `lib-phantom-probe.sh` + its two B1 consumers into one Python surface; rewire `verify-skill-called.sh` off sourced `lib-count-commits.sh` to the new CLI verb before deleting it.
- Follow the per-domain playbook recipe end-to-end; sequence so harnesses run once as a parity gate before bash deletion.

### Surfaces in scope
- `python/{git,gh,pr,push,merge,ci_monitor}.py`, `python/cli.py`, colocated `python/test_*.py`, `python/migrated-scripts.tsv`.
- `scripts/` — delete ~40 `.sh` + `.md` + `test-*.sh`; rewire `scripts/verify-skill-called.sh`.
- Call sites + stale-reference sweep across `skills/**`, `docs/`, `Makefile`, `.github/`, `README.md`, `SECURITY.md`.

### Open questions
- CLI namespace granularity (e.g. one `git` domain with many verbs vs finer domains) — defer to Step 2b plan + plan review.
- Total size is large; whether to keep one plan body or split is deferred to the Step 2b.5 size brake (operator already chose one consolidated plan).
