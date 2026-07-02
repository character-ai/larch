## Goal
Implement issue #6025: [IMPLEMENTING] [BUG] Run-log summaries under-report exec issues, warnings, and rejected counts.

## Implementation Plan
## Summary

Committed run-log summaries systematically disagree with their own sibling artifacts. Final summaries claim "Exec issues: 0 / Warnings: 0" while the same run's execution-issues.ndjson commits multiple entries; a round summary and its round-meta.json disagree on the rejected count; a manifest claims a step did not run while the timing report shows it ran. Operators and downstream analysis reading only the summary get a false clean bill.

## Original report

From the 2026-07-02 post-merge audit of the last 11 implement runs. Four independent instances observed in committed logs at 63ed17f18. This is pre-existing harness behavior surfaced by the audit, not a defect of the audited PRs.

## Reproduction scenario

In each cited run-log directory, compare final-summary.md counters against `wc -l execution-issues.ndjson`, and round-1/review-round-summary.md against round-1/round-meta.json.

## Expected behavior

Summary counters derive from the same source of truth as the committed sibling artifacts: final-summary counts match the ndjson entries surviving redaction/flush, round summaries match round-meta, and manifest steps_ran matches the timing ledger.

## Observed behavior

- larch-logs/implement/445D1144-4835-44B1-860C-183FA6E92CA1 (#5974 run): final-summary.md says "Exec issues: 0 / Warnings: 0"; execution-issues.ndjson has 4 entries (count re-verified during filing).
- larch-logs/implement/D5A9703D-6BF5-4F88-BB2B-D41DF184BBCF (#5888 run): same zero claim; the ndjson holds 1 transient Step 7a.1 warning plus one G-Skill-2 deviation warning duplicated 10 times across flushes (the duplication itself is a secondary defect).
- larch-logs/implement/5BCCC59E-81CA-49EA-806B-0D9B6F1BB701 (#5889 run): round-1/review-round-summary.md says "0 accepted, 7 rejected"; round-meta.json says REJECTED_COUNT=8 (raw and canonical).
- larch-logs/implement/7623E215-D6C5-4123-8334-D1EAB4B29278 (#5972 run): manifest.json steps_ran.step7a=false while timing-report.json records Step 7a running for 83 seconds.

## Root cause analysis

Uncertain. Inference: the final-summary writer counts an in-memory list that diverges from what the ndjson appender wrote (different lifecycle or dedup), the round-summary writer diverges from the round-meta writer, and steps_ran is stamped from a different signal than the timing ledger. Needs investigation in the writers listed under Affected files.

## Evidence

Committed artifacts in the four run-log directories above, at 63ed17f18. The 445D1144 ndjson count (4) was re-verified directly during filing.

## Affected files

- python/larch/report/final_report.py: final-summary counters.
- python/larch/report/run_log_flush.py: flush lifecycle, duplicate warning appends.
- python/larch/review/review_tally.py and the round-summary writer: accepted/rejected counters.
- python/larch/report/run_log_manifest.py: steps_ran stamping.

## Suggested fix(es)

- Derive final-summary counters by reading the committed execution-issues.ndjson at render time instead of an in-memory counter.
- Derive round-summary counts from round-meta.json.
- Dedupe identical warnings across flushes (stable key on step + code + message).
- Add a run-log consistency check (lint or tolerance harness) asserting summary counters match sibling artifacts.

## Open questions

- Is the 10x duplicated warning an append-idempotency bug worth a targeted fix, or accepted append-only semantics that the summary layer should dedupe at render time?

## Test plan
(no test plan section in plan-file)
