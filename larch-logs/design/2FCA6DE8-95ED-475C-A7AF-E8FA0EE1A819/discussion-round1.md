## Decision 1: Partition vs single plan
- **Question**: Design B1 (~40 git/gh/CI scripts) as one consolidated plan on #3670, or split into per-domain sub-issues first?
- **Resolution**: One consolidated plan on #3670. Cover all domains in a single plan; keep the umbrella's B1 grouping and its interdependencies intact. If the plan trips the size brake, resurface splitting then.
- **Source**: user

## Decision 2: Completeness bar
- **Question**: What is "done" for each absorbed script?
- **Resolution**: Full parity. Each script's behavior becomes importable Python functions + a `cli.py` verb; white-box harness semantics port to colocated pytest; the bash + its `.sh`/`.md`/`test-*.sh` siblings are deleted; manifest updated; `lint-retired-scripts` green. No shims, no `LARCH_*_IMPL` selector.
- **Source**: codebase (Definition of Done + docs/python-migration.md) and prior user preference for complete per-phase ports

## Decision 3: Call-site cutover boundary
- **Question**: Which consumers get repointed, and when?
- **Resolution**: Hard cutover of every live consumer in the same change — skill `.md`, docs, Makefile, CI workflow, and any bash that invoked the old script — to `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" <domain> <verb>`. Stale-reference sweep across `docs/`, `skills/**`, `README.md`, `SECURITY.md`, `.github/`.
- **Source**: codebase (docs/python-migration.md decision log: no shims, hard cutover)

## Decision 4: Sourced shell-library boundary
- **Question**: How to handle scripts that are `source`d (provide shell functions) rather than exec'd?
- **Resolution**: `lib-phantom-probe.sh` is sourced only by `rebase-checkpoint-probe.sh` and `phantom-probe-with-warn.sh` — both in B1 — so the source dependency collapses when all three fold into one Python module + two CLI verbs. `lib-count-commits.sh` is sourced by `verify-skill-called.sh` (NOT in B1) for `count_commits()`; deleting it requires rewiring `verify-skill-called.sh` to call the new CLI verb. That single out-of-list edit is in-scope (required to satisfy the no-shims deletion).
- **Source**: codebase (grep of `source`/`.` consumers)

## Decision 5: ship-pr.sh boundary
- **Question**: Does B1 touch the legacy `scripts/ship-pr.sh` and its inlined copies?
- **Resolution**: No. `ship-pr.sh` keeps its own internal copies untouched; E1 retires it later. B1 consolidates only the standalone scripts and their consumers. Reuse the already-ported `python/{git,gh,pr,push,merge,ci_monitor}.py` surfaces (from the ship-pr port) rather than re-porting.
- **Source**: codebase (issue Notes + python/README.md Phase 5)

## Decision 6: Hooks
- **Question**: Do any Claude Code hooks call the absorbed scripts (hooks stay bash)?
- **Resolution**: No hook references any absorbed script (grep of `hooks/`). No hook cutover needed.
- **Source**: codebase (grep of `hooks/`)
