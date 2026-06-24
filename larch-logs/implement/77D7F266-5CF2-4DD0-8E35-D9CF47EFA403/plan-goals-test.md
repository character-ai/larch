## Goal
Implement issue #5113: [IMPLEMENTING] Keyword-only args: plan-review-execution [#5002 part 2/10].

## Implementation Plan
Part 2 of 10 of the #5002 keyword-only enforcement. Mechanizes a criterion-2 item from #4659; pairs with G-Py-3. Umbrella: #5002. **Blocked by part 0** (lint + baseline).

## Scope

In the **plan-review-execution** modules (10 files, ~9319 lines), add a leading `*` to every in-scope `def` / `async def` (2 or more non-`self`/`cls` params), then update all call sites to pass those arguments by name. Remove the converted defs from the part-0 baseline.

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

Note: the `def` edits are confined to the files above, but call-site updates may touch other `python/` source files. That is expected and safe under the single-runner invariant.

## Test files: fix only what breaks

Test files are not an audit target. No test-defined function gets `*`; no test local is touched. Sole exception: when adding `*` to one of the source functions above breaks an existing positional call in a test, switch that one call to keyword form, solely to keep `make py-test` green. This matches the #5002 umbrella decision.

## Carve-outs (do not add `*`)

- Single-parameter functions.
- Dunders and operator/protocol methods with fixed signatures.
- Signatures dictated by an external API or callback contract.

## Excluded (do not touch, stated in every chunk and the umbrella)

- All test files: `python/test_*.py` and `python/conftest.py`.
- Everything under `larch-logs/`.
- Every `.py` outside `python/` (skill scripts, repo-root helpers).

Audit surface is `python/` non-test source only.

## Acceptance

- In-scope defs in the listed files are keyword-only; all call sites updated, including the minimal test call-site fixes above.
- Converted defs removed from the part-0 baseline.
- `make py-lint` and `make py-test` green.

## Test plan
(no test plan section in plan-file)
