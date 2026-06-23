## Goal
Implement issue #5107: [IMPLEMENTING] Type local vars: github-issues-infra [#5001 part 8/10].

## Implementation Plan
Part 8 of 10 of the #5001 local-variable typing audit. Enacts **G-Py-2** from #4659. Umbrella: #5001.

## Scope

Add type annotations to non-obvious local variables in the **github-issues-infra** modules only (13 files, ~10384 lines):

- `python/gh.py` (~1751 lines)
- `python/git.py` (~1678 lines)
- `python/combine_issues.py` (~1203 lines)
- `python/file_oos.py` (~1110 lines)
- `python/tracking_issue.py` (~1028 lines)
- `python/issue_create.py` (~969 lines)
- `python/deps_audit.py` (~926 lines)
- `python/oos_filer.py` (~832 lines)
- `python/issue_query.py` (~238 lines)
- `python/oos.py` (~214 lines)
- `python/blocker.py` (~177 lines)
- `python/oos_disposition.py` (~136 lines)
- `python/issue_block.py` (~122 lines)

## What to annotate

Locals whose type is not obvious from the right-hand side. Keep diffs surgical. Touch only the files listed above.

## Carve-outs (leave un-annotated, obvious RHS)

`count = 0`, loop targets, `x = Foo()`, a value returned by an already-typed call. Annotating these adds noise.

## Not lint-enforceable

ruff `ANN` covers signatures, not locals (see #5003). This is a manual audit pass for this domain.

## Excluded (do not touch, stated in every chunk and the umbrella)

- All test files: `python/test_*.py` and `python/conftest.py`.
- Everything under `larch-logs/`.
- Every `.py` outside `python/` (skill scripts, repo-root helpers).

Audit surface is `python/` non-test source only.

## Acceptance

- Non-obvious locals in the listed files carry annotations.
- `pyright` clean; `make py-test` green.
- No source changes outside the listed files.

## Test plan
(no test plan section in plan-file)
