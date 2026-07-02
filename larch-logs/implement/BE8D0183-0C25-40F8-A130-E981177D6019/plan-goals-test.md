## Goal
Implement issue #6030: [IMPLEMENTING] [BUG] #5888 residuals: dead _run_apply, missing promised tests, stale shard nodeids.

## Implementation Plan
## Summary

Three non-runtime residuals from #5888 / PR #6010 (cost-rebalance): `_run_apply` in plan_review.py is dead runtime code kept alive with pyright suppressions instead of the plan-promised refactor; two plan-promised tests were never written; and python/shard-assignments.json retains 14 nodeids for the deleted revise_waterfall tests.

## Original report

From the 2026-07-02 post-merge audit of #5888 / PR #6010 at 63ed17f18. The audit found the code change itself complete, correct, and test-verified; these are the residual shortfalls. That run's review accepted 0 of 8 findings, so none of these were forced in-PR.

## Reproduction scenario

- Grep production callers of `_run_apply` in python/larch/design/plan_review.py: only a test references it after inline Gate B routing replaced the apply path.
- Search the test suite for awaiting-apply and legacy-awaiting-revise resume re-bail assertions and for a round-meta.json-after-inline-Gate-B assertion: absent.
- Read python/shard-assignments.json around lines 717-730: nodeids of deleted revise_waterfall tests remain.

## Expected behavior

Dead code refactored into the plan's intended resume helper or deleted; the two promised tests exist; shard data regenerated after test deletion.

## Observed behavior

As described per item. The stale shard nodeids are harmless at runtime (the sharder treats unknown ids as data and /rebalance-tests regenerates; the migration lint explicitly excludes the file), so that sub-item is cosmetic.

## Root cause analysis

Plan shortfalls in an otherwise complete implementation: the plan said to refactor `_run_apply` into a resume helper and to add the two tests; the implementation kept the function with suppressions and skipped the tests. Observation from the plan text and shipped diff comparison.

## Evidence

- python/larch/design/plan_review.py:233-261 (`_run_apply` with pyright suppressions, no production caller) at 63ed17f18.
- The #5888 issue's vetted in-body plan (test list) versus the shipped test files.
- python/shard-assignments.json:717-730.

## Affected files

- python/larch/design/plan_review.py.
- python/tests/design/ plan-review tests.
- python/shard-assignments.json (regenerate via /rebalance-tests).

## Suggested fix(es)

Delete or refactor `_run_apply` per the plan's resume-helper intent; add the awaiting-apply and legacy-awaiting-revise re-bail tests and the round-meta-after-Gate-B assertion; regenerate shard assignments.

## Open questions

None identified.

## Test plan
(no test plan section in plan-file)
