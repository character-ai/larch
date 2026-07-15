## Goal
Implement issue #7353: [IMPLEMENTING] [BUG] waterfall-dropped reviewer slots and aggregator insufficient-input not logged to execution-issues.md.

## Implementation Plan
## Summary

When the waterfall dispatcher drops a reviewer slot (`collector-failure` reason) and the aggregator receives insufficient input for round 2, neither event is recorded in `execution-issues.md`. The final summary reports "Exec issues: 0" despite a silently dropped slot and a degraded round-2 panel. Operators have no audit trail in the run log.

## Original report

root cause of why despite degraded panel on 2 review rounds, no Execution Issues was output in final report (session CEEEAB76-8109-4788-919E-946B3AF6C1C1, issue #7031).

## Reproduction scenario

1. Run `/design` on any issue where at least one Codex reviewer's launcher exits with code 1 (non-OK).
2. The waterfall dispatcher drops the slot and creates `plan-review/round-1/dropped-{slot}-codex-collector-failure.txt`.
3. Round 2 runs with a panel pruned to 1 reviewer → `AGGREGATOR_STATUS=insufficient-input`.
4. Observe that `execution-issues.md` does not exist in `$DESIGN_TMPDIR`.
5. Observe that the final summary reports "Exec issues: 0".

## Expected behavior

Both events should appear in `execution-issues.md` and be counted in the final summary:

1. A waterfall-dropped reviewer slot (reason `collector-failure`) should produce a per-slot `run-log append-failure` entry under category "External Reviewer Issues".
2. `AGGREGATOR_STATUS=insufficient-input` (too few reviewers for the aggregator to produce meaningful output) should produce a warning entry, because it means the round produced no useful review coverage.

## Observed behavior

- `execution-issues.md` was never created.
- Round-1 `round-summary.env` shows `COLLECT_FAILURE_COUNT=0` even though Codex-Pragmatic was dropped by the waterfall.
- Round-2 `round-summary.env` shows `AGGREGATOR_STATUS=insufficient-input` with no corresponding execution issue.
- Final summary: "Exec issues: 0", "Warnings: 0".

## Root cause analysis

Two separate gaps.

**Gap 1 — waterfall dispatcher drops skip execution-issues.md.**

`_compose_findings_from_collector` (in `python/larch/review/plan_review_round.py:486`) increments `failure_count` and calls `run-log append-failure` only for collector records with `STATUS != OK`. A slot dropped by `agent dispatch-waterfall` before collection leaves no collector record; `_compose_findings_from_collector` never processes it, so `COLLECT_FAILURE_COUNT=0` and no execution issue is logged.

The waterfall does call `_preserve_drop_diagnostic` (`python/larch/agents/agent_waterfall.py:1007`) and writes the `dropped-*-collector-failure.txt` file, but that code path never calls `run-log append-failure` or writes to `execution-issues.md`.

**Gap 2 — AGGREGATOR_STATUS=insufficient-input not logged.**

When round 2 has only 1 reviewer, the aggregator returns `AGGREGATOR_STATUS=insufficient-input`. The round loop records this in `round-summary.env` but no code path logs it to `execution-issues.md`. The degraded state is visible in the round artifacts but invisible in the final summary's execution-issue count.

## Evidence

- `plan-review/round-1/dropped-codex-plan-pragmatic-codex-collector-failure.txt`: exists (created by `_preserve_drop_diagnostic`)
- `plan-review/round-1/round-summary.env`: `COLLECT_FAILURE_COUNT=0 COLLECT_OK_COUNT=9`
- `plan-review/round-1/reviewer-status.tsv`: `Codex-Pragmatic skipped` (no collector record → "skipped")
- `plan-review/round-2/round-summary.env`: `AGGREGATOR_STATUS=insufficient-input LOOP_STATUS=zero-findings-degraded-panel`
- `execution-issues.md`: absent from `$DESIGN_TMPDIR`
- `python/larch/agents/agent_waterfall.py:1007–1044`: `_preserve_drop_diagnostic` and `_write_drops` — no `run-log append-failure` call
- `python/larch/review/plan_review_round.py:486–521`: `_compose_findings_from_collector` — only logs for collector records with `STATUS != OK`

## Affected files

- `python/larch/agents/agent_waterfall.py`: `_write_drops` / `_preserve_drop_diagnostic` — drop diagnostics not reported to execution-issues
- `python/larch/review/plan_review_round.py`: `_compose_findings_from_collector` — only counts collector-record failures, not pre-collection dispatcher drops
- `python/larch/review/plan_review_round.py` (or round_runner.py): `AGGREGATOR_STATUS=insufficient-input` not logged to execution-issues
- `python/tests/review/test_plan_review_round.py`: coverage for dispatcher-dropped slot logging

## Suggested fix(es)

1. **Dispatcher-drop logging**: in `_write_drops` (`agent_waterfall.py`), after calling `_preserve_drop_diagnostic`, invoke `run-log append-failure` (or equivalent) with the dropped-slot details (slot name, tool, reason, diag path) and category "External Reviewer Issues". This mirrors the `_compose_findings_from_collector` path but runs for pre-collection drops.

2. **Insufficient-input logging**: wherever `AGGREGATOR_STATUS=insufficient-input` is set, append a warning entry to `execution-issues.md`. This ensures rounds that fail to aggregate are surfaced in the final summary.

## Open questions

- Should dispatcher drops increment `COLLECT_FAILURE_COUNT` in `round-summary.env` as well, or should they be tracked under a separate `DISPATCH_DROP_COUNT` key?
- Should `AGGREGATOR_STATUS=insufficient-input` be surfaced as a `Warnings` entry or an `External Reviewer Issues` entry?

## Test plan
(no test plan section in plan-file)
