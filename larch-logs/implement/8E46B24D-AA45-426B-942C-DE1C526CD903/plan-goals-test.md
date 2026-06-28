## Goal
Implement issue #5791: [IMPLEMENTING] [BUG] required-files.tsv lists plan-review-tally.json + version-bump-reasoning.md as required, but neither is written → required-file-presence fails on 100% of /implement runs.

## Implementation Plan
**Summary.** `docs/run-logs-required-files.tsv` lists two batches as required that current `/implement` runs never write, so the `audit-runs` `required-file-presence` scan reports `fail` on 100% of runs (216/216 in implement audit #5789, versions 51.3.9–52.1.9).

**Details.**

- `version-bump-reasoning.md` (condition `step8`): Phase 1 (#3364) removed it from the `/implement` ship path; no implement-side write site remains. `docs/run-logs.md` documents the removal. The manifest entry is stale.
- `plan-review-tally.json` (condition `always`): present in 0/246 committed run dirs. Code has copy sites (`python/larch/state/bootstrap.py`, `python/larch/review/voting.py`) but the artifact only materializes when plan-review voting runs in-process; for `/implement`, plan review now runs in `/design`, so it is effectively never produced.

**Impact.** The audit `required-file-presence` scan and the run-log completeness contract are out of sync with the actual Phase-1 ship path. Every implement run reports a false required-file failure, which masks genuine missing-file regressions.

**Suggested fix.** Relax both manifest conditions (mark informational/conditional or remove), OR restore the writes (emit a `plan-review-tally.json` stub for `/implement` runs as `docs/run-logs.md` implies). Update `docs/run-logs-required-files.tsv` and `docs/run-logs.md` together.

**Evidence.** Implement audit report #5789.

## Test plan
(no test plan section in plan-file)
