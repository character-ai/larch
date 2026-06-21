## Proposed Design Outline

### Goals
- Eliminate the two remaining sourced bash libraries: `lib-plan-optional-trailers.sh` + `.awk` (design) and `lib-implement-clone-tag.sh` (implement), per AGENTS.md "no shared bash libraries."
- Keep optional-trailer plan-size gating and clone-tag tmpdir validation behavior byte-identical.
- Leave `make lint-retired-scripts` and the residual-bash inventory clean.

### Non-goals
- No re-port of optional-trailers logic; it already lives in `python/plan_quality.py`.
- No behavior change to plan-size gating or `/implement` Step 8 seed/ship flow.
- No broader bash sweep; scope is exactly these two libs.

### Approach sketch
- Design side is retirement-only: delete the dead `lib-plan-optional-trailers.sh` + `.awk`; port any unique trailer-harness assertions into `python/test_plan_quality.py`; delete the bash trailer harnesses.
- Implement side: add a `cli.py` verb that emits `CLONE_TAG_FULL=` / `EXPECTED_TMPDIR_BASENAME_PREFIX=`; repoint `step-8-seed-initial.sh` + `step-8-ship.sh` to eval it; delete `lib-implement-clone-tag.sh`.
- Housekeeping: delete `.md` siblings; prune `scripts/residual-bash-paths.txt`; append `python/migrated-scripts.tsv` with `#4971`; fix prose pointers in SKILL.md/docs.

### Surfaces in scope
- `skills/design/scripts/lib-plan-optional-trailers.{sh,awk,md}`, `skills/design/scripts/test-trailer-*.{sh,md}`
- `python/plan_quality.py` (parity check), `python/test_plan_quality.py`
- `skills/implement/scripts/lib-implement-clone-tag.{sh,md}`, `step-8-seed-initial.sh`, `step-8-ship.sh`, `test-step-8-ship.sh`
- `python/cli.py` registry + the implement-side Python module hosting the verb
- `scripts/residual-bash-paths.txt`, `python/migrated-scripts.tsv`, prose pointers in SKILL.md / docs

### Open questions
- Exact home module + verb name for the clone-tag derivation (resolved in plan drafting; likely the existing implement-domain Python module).
