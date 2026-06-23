## Goal
Implement issue #5111: [IMPLEMENTING] Keyword-only args lint + baseline, warning-only [#5002 part 0/10].

## Implementation Plan
Part 0 of the #5002 keyword-only enforcement. Mechanizes a criterion-2 item from #4659; pairs with G-Py-3. Umbrella: #5002. **Blocks parts 1-10.**

## Goal

Build a custom AST lint that flags any `def` / `async def` in `python/` non-test source with 2 or more non-`self`/`cls` parameters that lacks a leading `*`. Ship it **warning-only** behind a **baseline file** listing every currently-failing def, mirroring the existing `python/lint_complexity_baseline.py` pattern. New violations fail; baselined ones only warn. Each conversion chunk (parts 1-10) removes its converted defs from the baseline; enforcement becomes total once the baseline empties.

## Scope

- New lint module under `python/` (for example `lint_keyword_only.py`) plus its baseline file.
- Wire into `make lint` and pre-commit per repo convention.
- Generate the initial baseline across all non-test `python/` source.

## Carve-outs (lint must not flag)

- Single-parameter functions.
- Dunders and operator/protocol methods with fixed signatures (`__eq__`, `__enter__`, and similar).
- Signatures dictated by an external API or callback contract.
- `self` and `cls` are never counted.

## Excluded (do not touch, stated in every chunk and the umbrella)

- All test files: `python/test_*.py` and `python/conftest.py`.
- Everything under `larch-logs/`.
- Every `.py` outside `python/` (skill scripts, repo-root helpers).

Audit surface is `python/` non-test source only.

## Acceptance

- Lint present, wired into `make lint` and pre-commit, warning-only via the baseline.
- Baseline lists every currently-failing non-test `python/` def.
- `make py-lint` and `make py-test` green.

## Test plan
(no test plan section in plan-file)
