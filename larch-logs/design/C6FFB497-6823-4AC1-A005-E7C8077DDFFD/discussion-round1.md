## Decision 1: Scope — which deferred libs does #3780 retire now
- **Question**: #3780 lists 4 deferred libs, but 2 are already migrated and 1 is still bash-hook-sourced. Which are in scope for this run?
- **Resolution**: In scope = `scripts/lib-design-tmpdir.sh` ONLY. Out of scope: `lib-validate-meta-path.sh` (already migrated #4333) and `lib-finalize-state-keys.sh` (already migrated #3690) — both already deleted and in `python/migrated-scripts.tsv`, nothing to do. `skills/implement/scripts/lib-resolve-implement-tmpdir.sh` is deferred (still sourced by 2 bash hooks; not ported).
- **Source**: user

## Decision 2: Disposition of the hook-blocked lib
- **Question**: How to track `lib-resolve-implement-tmpdir.sh` (hook-blocked; no hook-overhaul issue exists)?
- **Resolution**: Split it into a NEW follow-up tracking issue (to be ported after a future hook overhaul) and drop it from #3780's scope so #3780 can close once `lib-design-tmpdir.sh` is retired. Record as an out-of-scope follow-up.
- **Source**: user

## Decision 3 (hard constraint): Reuse the existing Python validator
- **Question**: Does the design-tmpdir validator need to be (re)written in Python?
- **Resolution**: No. `python/session_env.py::validate_design_tmpdir(candidate) -> (bool, str)` already exists and is used by `plan_review.py`, `plan_review_tally.py`, and `rendering.py`. Reuse it; do NOT reimplement the validation logic. The remaining gap is a thin `cli.py` verb so bash callers can reach it (no `session validate-design-tmpdir` verb exists yet).
- **Source**: codebase

## Decision 4 (hard constraint): The 14 live bash sourcers must keep working
- **Question**: What must not break?
- **Resolution**: 14 live bash scripts still `source scripts/lib-design-tmpdir.sh` and call `larch_design_tmpdir_validate "$X" || exit 2` (design-step3-review.sh, design-step3-entry.sh, design-step2b-postplan.sh, design-step3-mav.sh, design-step35-settle.sh, design-step3-continuation-entry.sh, design-failure-report.sh, plan-review-continuation.sh, design-stage-terminal-state.sh, plus debug/test scripts). Each must be repointed to the new CLI verb with identical fail-fast (exit 2) semantics before the bash lib is deleted. Pause-before-work ordering in the wrappers must be preserved (test-design-structure.sh enforces it).
- **Source**: codebase + issue DoD

## Decision 5 (definition of done): ledger + lint gates
- **Question**: What proves the retirement is complete?
- **Resolution**: Delete `scripts/lib-design-tmpdir.sh` + `.md` + `scripts/test-lib-design-tmpdir.sh` + `.md`; append all four to `python/migrated-scripts.tsv` tagged `#3780`; remove the `python/checks.py` allowlist entry + the `Makefile` `test-lib-design-tmpdir` target + any `agent-lint.toml` allowlist entry; `make lint-retired-scripts && make lint && make py-lint && make py-test` all green.
- **Source**: issue
