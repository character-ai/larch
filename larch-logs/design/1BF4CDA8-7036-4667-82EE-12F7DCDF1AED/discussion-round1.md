## Decision 1: Mechanism — per-file-ignores baseline
- **Question**: Which mechanism holds new code to the complexity budget while grandfathering existing files?
- **Resolution**: Re-enable the 5 complexity rules (C901, PLR0911, PLR0912, PLR0913, PLR0915) globally in `python/ruff.toml` by removing them from `[lint] ignore`; grandfather currently-violating production files under `[lint.per-file-ignores]`. Pure config + docs change. No changed-files lint lane. Refactors inside a grandfathered file are not caught until that file's ignore entry is removed.
- **Source**: user

## Decision 2: Enforcement — hard error
- **Question**: Should over-budget new code fail the build or just warn?
- **Resolution**: Hard error. New/over-threshold code fails `make py-lint` and CI. ruff has no native warning tier; grandfathering keeps existing files green.
- **Source**: user

## Decision 3: Thresholds — ruff defaults
- **Question**: Use ruff's default complexity thresholds or relax them?
- **Resolution**: ruff defaults (C901 max-complexity 10, PLR0911 max-returns 6, PLR0912 max-branches 12, PLR0913 max-args 5, PLR0915 max-statements 50). No threshold overrides.
- **Source**: user

## Decision 4: Test files — exempt
- **Question**: Hold test files to the budget or exempt them?
- **Resolution**: Exempt. Add the 5 complexity codes to the existing `test_*.py` block in `[lint.per-file-ignores]`. This also keeps the grandfather baseline to production files only.
- **Source**: user

## Decision 5: Out of scope — no existing-violation fixes
- **Question**: Should this work fix existing complexity violations?
- **Resolution**: No. Existing god-functions are grandfathered, not refactored. Splitting them is a separate item.
- **Source**: user (issue Out-of-scope)

## Decision 6: Hard constraint — existing tree stays green
- **Question**: What must not break?
- **Resolution**: `make py-lint` (`cd python && ruff check .`) and CI must stay green for the existing `python/` tree after the change. Lint scope is `python/` only; skill-local Python is unaffected.
- **Source**: codebase (Makefile py-lint-main, docs/linting.md)
