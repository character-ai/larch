## Goal
Implement issue #5102: [IMPLEMENTING] Type local vars: plan-review-quality [#5001 part 3/10].

## Implementation Plan
Part 3 of 10 of the #5001 local-variable typing audit. Enacts **G-Py-2** from #4659. Umbrella: #5001.

## Scope

Add type annotations to non-obvious local variables in the **plan-review-quality** modules only (5 files, ~7358 lines):

- `python/plan_quality.py` (~2446 lines)
- `python/plan_review.py` (~2407 lines)
- `python/plan_review_round.py` (~922 lines)
- `python/plan_review_panel.py` (~831 lines)
- `python/plan_review_tally.py` (~752 lines)

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
