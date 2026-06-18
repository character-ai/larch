# Design Discussion — Round 1 (scope & constraints)

Issue #4717: Speed up the `python-lint` CI job (currently ~166s, the CI bottleneck).
All decisions below were resolved with the operator during Step 1c.

## Profiling evidence (real CI run 27777101922, job `python-lint`)
- Job total **166s**; fixed overhead (checkout 17s + setup + cached pip-install 4s) ~28s.
- Linter step **137s** = `cd python && ruff check . && pylint -j 1 . && pyright`.
- ruff ~0.1s; **pylint `-j1` ~100s** (single-process — the bottleneck); pyright ~36s.
- Root cause: `PYLINT_JOBS = 0 if sysconf(SC_SEM_NSEMS_MAX) >= 0 else 1` returns `-1` on the Linux runner, so pylint silently runs single-process. (Returns 87381 on macOS → all cores locally.)
- Estimate: pylint on the runner's ~4 cores ~40-50s (pylint `-j` scales ~2-3X). After that fix pylint(~45s) ≈ pyright(~36s) → balanced.

## Decision 1: Overlap strategy / job structure
- **Question**: How to reach ≥2X — split pyright into its own job, run tools concurrently in one job, or fix pylint `-j` only?
- **Resolution**: Split **pyright** into its own parallel CI job; keep **ruff + pylint** together in `python-lint`. Also fix pylint to use all cores on CI (the root-cause lever). Mirrors the `python-lint-duplicate-code` split (#4480). Projected wall ~70s (~2.3X).
- **Source**: user

## Decision 2: pylint `-j` mechanism
- **Question**: How to make pylint parallelize on Linux CI without breaking restricted local sandboxes (the reason the sysconf probe exists)?
- **Resolution**: Force `PYLINT_JOBS=0` in the CI workflow env on the `python-lint` job; keep the Makefile `sysconf` auto-detect as the local default/fallback. Do **not** rewrite the Makefile probe; do **not** hardcode `-j 0` in the Makefile default.
- **Source**: user

## Decision 3: duplicate-code scope
- **Question**: Is `python-lint-duplicate-code` in scope?
- **Resolution**: **Out of scope.** Its similarity checker must run `-j 1` by design (#4480) and can't be parallelized the same way. A **separate issue is already undergoing design** to speed up `python-lint-duplicate-code`, so this design must not touch it or file any follow-up/OOS for it. Informational only: after this fix that job (~121s) may become the longest Python CI job.
- **Source**: user

## Decision 4: ruff handling
- **Question**: Should ruff be split into its own job?
- **Resolution**: **No.** ruff runs ~0.1s; keep it bundled with pylint in `python-lint`.
- **Source**: user

## Decision 5: success target
- **Question**: What defines "done"?
- **Resolution**: Reduce the `python-lint` job wall-clock by **at least 2X** (166s → ≤~83s). Validated by CI timing; not a CI-enforced time gate.
- **Source**: user

## Hard constraints (must not break)
- Do not reduce lint coverage: same ruff checks, full pylint checker set, and pyright must all still run and gate CI.
- Keep restricted-local-sandbox fallback intact (Makefile auto-detect unchanged; only CI env forces `PYLINT_JOBS=0`).
- The new pyright job must gate merges like the current pyright run does. **Risk to flag**: if branch protection lists `python-lint` as a required status check, the new pyright job must be added to required checks in GitHub settings (outside this repo) or pyright failures stop blocking merges.

## Non-goals / out of scope
- `python-lint-duplicate-code` (handled by a separate in-flight design issue — do not touch or file OOS for it), `python-tests`, and splitting `ruff` into its own job.
