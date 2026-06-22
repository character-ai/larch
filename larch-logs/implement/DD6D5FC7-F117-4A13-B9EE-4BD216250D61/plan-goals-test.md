## Goal
Implement issue #5101: [IMPLEMENTING] Type local vars: plan-review-execution [#5001 part 2/10].

## Implementation Plan
Part 2 of 10 of the #5001 local-variable typing audit. Enacts **G-Py-2** from #4659. Umbrella: #5001.

## Scope

Add type annotations to non-obvious local variables in the **plan-review-execution** modules only (10 files, ~9319 lines):

- `python/review_and_fix.py` (~3292 lines)
- `python/review_pipeline.py` (~2332 lines)
- `python/review_tally.py` (~1049 lines)
- `python/review_aggregate.py` (~948 lines)
- `python/review_dispatch.py` (~460 lines)
- `python/compose_review.py` (~371 lines)
- `python/review_test_support.py` (~611 lines)
- `python/review_types.py` (~114 lines)
- `python/review_phase_detail.py` (~94 lines)
- `python/self_review_tally.py` (~48 lines)

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
