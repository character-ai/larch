## Decision 1: Per-package realization mechanism
- **Question**: How should "re-tighten per-package complexity enforcement" be realized mechanically?
- **Resolution**: Reuse the two existing grandfather mechanisms. Drop obsolete `python/ruff.toml` per-file-ignores and regenerate `python/complexity-baseline.json`. Do NOT introduce a new per-package config, directory-scoped ruff sections, or a new linter mode. "Per package" is the lens for deciding what to clean and how to document it.
- **Source**: user

## Decision 2: Scope depth (bookkeeping vs refactor)
- **Question**: Does this issue include reducing remaining complexity, or only removing now-obsolete suppressions?
- **Resolution**: Bookkeeping only. Remove only the suppressions and baseline rows the splits already made obsolete (as measured by live ruff). Genuinely-still-complex functions remain grandfathered. No new function decomposition in this issue — that belonged to splits 2/14–12/14.
- **Source**: user

## Decision 3: Per-file-ignore tightening granularity
- **Question**: How aggressively should obsolete per-file-ignore entries be tightened?
- **Resolution**: Per-code, maximal. For each listed file, drop every complexity code it no longer violates; remove the whole per-file entry only when fully clean. Matches the documented cleanup procedure in `docs/linting.md`.
- **Source**: user

## Decision 4: Hard constraint — `make py-lint` stays green
- **Question**: What must not break?
- **Resolution**: `make py-lint` (→ `py-lint-checks-fast`: `cd python && ruff check .` + `python/cli.py lint complexity-baseline`) MUST be green after the change. An ignore code may be removed only when ruff confirms the file no longer violates it; the regenerated baseline must match live ruff output. Acceptance criterion.
- **Source**: codebase / issue acceptance

## Decision 5: Hard constraint — scope of files/codes touched
- **Question**: What existing behavior must be preserved?
- **Resolution**: Only touch the five complexity codes (`C901`, `PLR0911`, `PLR0912`, `PLR0913`, `PLR0915`) in production grandfathering. Preserve: (a) all non-complexity `ignore` entries in both ruff configs; (b) test-facing per-file-ignores and linter exemptions (`test_*.py`, `conftest.py`, `test_support.py`, `review_test_support.py`) — these are permanent, not split-removable; (c) the `ruff-complexity-audit.toml` audit config's structure (it intentionally omits production ignores). Baseline must stay byte-canonical (sorted, 2-space, trailing newline) via `--write`.
- **Source**: codebase

## Decision 6: Non-goal — other ratchets untouched
- **Question**: What does the user explicitly NOT want?
- **Resolution**: Do not modify the subprocess-via-runner, env-via-config-constant, or layering ratchets/baselines. Do not change the complexity enforcement mechanism itself. Do not add new make targets beyond what already exists (`regen-complexity-baseline` is reused).
- **Source**: codebase / Decision 1

## Decision 7: Empirical/mechanical determination of "clean"
- **Question**: How is "now clean per package" established (must-have)?
- **Resolution**: Determined mechanically from live ruff output, not asserted. The plan describes the procedure (regenerate baseline via `make regen-complexity-baseline`; per-file probe to find still-violated codes); exact per-file/per-row reductions are produced at implement time and cannot be pre-stated as fixed numbers. Acceptance is "no split-removable debt remains," verified by a clean `make py-lint`.
- **Source**: codebase
