## Goal
Implement issue #5104: [IMPLEMENTING] Type local vars: ship-pr-release [#5001 part 5/10].

## Implementation Plan
Part 5 of 10 of the #5001 local-variable typing audit. Enacts **G-Py-2** from #4659. Umbrella: #5001.

## Scope

Add type annotations to non-obvious local variables in the **ship-pr-release** modules only (13 files, ~8729 lines):

- `python/ship.py` (~2521 lines)
- `python/finalize.py` (~1190 lines)
- `python/pr_body.py` (~840 lines)
- `python/version_bump.py` (~654 lines)
- `python/rebase.py` (~632 lines)
- `python/merge.py` (~618 lines)
- `python/pr.py` (~488 lines)
- `python/push.py` (~439 lines)
- `python/closeout.py` (~400 lines)
- `python/step_7a.py` (~354 lines)
- `python/release_finish.py` (~231 lines)
- `python/release_prepare.py` (~230 lines)
- `python/promote_release.py` (~132 lines)

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
