## Goal
Implement issue #4480: [IMPLEMENTING] Lower pylint duplicate-code min-similarity-lines from 20 to optimal (~8) and fix R0801 violations.

## Implementation Plan
## Context

A new CI job `python-lint-duplicate-code` runs pylint's duplicate-code (R0801) checker in a dedicated single-process pass (`pylint --disable=all --enable=duplicate-code -j 1 .`). It was split out of the main `python-lint` job because the similarities checker is incorrect under `-j>1`: each worker process sees only a slice of files, so cross-worker duplicates are missed and the reported cluster set varies run-to-run. Verified on pylint 4.0.5 (the CI pin): at `-j 0` the count matched single-process (72) but the cluster members differed.

To land the split with a green gate, `python/.pylintrc` `[SIMILARITIES] min-similarity-lines` was temporarily raised from 5 to **20**, which yields **0** violations today. This is an interim value, not the target.

## Goal

Lower `min-similarity-lines` to the optimal level and fix all R0801 duplicate-code violations that surface, so the gate stays green at the lower (more sensitive) threshold.

## Violation count by threshold (measured, pylint 4.0.5, single-process)

| min-similarity-lines | R0801 clusters |
|---|---|
| 5 (original repo value) | 72 |
| 8 | 17 |
| 12 | 7 |
| 15 | 1 |
| 20 (current interim) | 0 |

## Suggested optimal: 8

Rationale:
- The jump from 8 (17 clusters) down to 5 (72) is dominated by 5-7 line near-duplicates, which in this codebase are mostly test boilerplate, argparse scaffolding, and similar dict/setup blocks. Extracting those tends to hurt readability more than it helps.
- Duplicates of 8+ lines are more likely genuine copy-paste worth consolidating.
- 8 yields a manageable 17 clusters.
- Choose 5 instead only for maximum strictness (the repo's original value), accepting ~72 clusters to address.

Final value is the implementer's call; 8 is the recommendation.

## Steps

1. Edit `python/.pylintrc` `[SIMILARITIES] min-similarity-lines` from 20 to the chosen optimal (recommended 8).
2. List violations: `make py-lint-duplicate-code` (or `cd python && pylint --disable=all --enable=duplicate-code -j 1 .`).
3. For each R0801 cluster: prefer removing the duplication (extract a shared helper, fixture, or constant) where it improves clarity; where duplication is intrinsic (e.g. parallel test cases) and extraction would hurt readability, add a scoped `# pylint: disable=duplicate-code` with a one-line justification, or tune the `[SIMILARITIES]` ignore-* options.
4. Re-run until clean. Confirm both `make py-lint` and `make py-lint-duplicate-code` pass.
5. Keep the duplicate-code pass at `-j 1` (it is incorrect under `-j>1`, see Context).
6. Keep `duplicate-code` in the `disable=` list in `python/.pylintrc` so the main `python-lint` job does not run it; the dedicated job force-enables it via `--enable`.

## Acceptance

- `min-similarity-lines` lowered to the optimal value.
- `python-lint-duplicate-code` CI job green at that threshold.
- No new `# pylint: disable=duplicate-code` without a justification comment.

## Background

Introduced alongside the CI split that adds the `python-lint-duplicate-code` job and the `make py-lint-duplicate-code` target.

## Test plan
(no test plan section in plan-file)
