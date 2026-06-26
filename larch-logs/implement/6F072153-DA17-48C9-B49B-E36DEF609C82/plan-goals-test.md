## Goal
Implement issue #5444: [IMPLEMENTING] [BUG] /design final report Review Phase Detail: empty Time and Cost columns.

## Implementation Plan
## Summary

The `/design` final report **Review Phase Detail** table renders `—` in **every** Time and Cost cell (each round and the total). The design plan-review loop does not record per-round timing in the format the renderer reads. Cost is empty as a knock-on effect: per-round cost is filtered to the per-round **time window**, so a missing window also zeroes Cost.

This affects `/design` only. The `/implement` Review Phase Detail table is unaffected; it records round timing through the canonical writer.

Analysis is from code inspection. The `/design` run that produced the symptom cleaned up its session tmpdir at Step 6, so the live `timing-ledger.tsv` was not re-inspected; the "no rows written" conclusion follows from the absence of a loop callsite, not from reading the deleted ledger.

## Symptom (from the issue #5393 run)

| Round | Suggestions | Accepted | OOS proposed | OOS accepted | Time | Cost | Reviewers |
|--:|--:|--:|--:|--:|:--|--:|--:|
| 1 | 8 | 2 | 2 | 0 | — | — | 8 |
| 2 | 8 | 3 | 4 | 0 | — | — | 8 |
| 3 | 2 | 1 | 0 | 0 | — | — | 3 |
| 4 | 3 | 0 | 1 | 0 | — | — | 3 |
| **Total (round-sum)** | **21** | **6** | **7** | **0** | **—** | **—** | **22** |

Both `Time` and `Cost` are `—` for every round and the total, even though the run-level cost computed fine (TOTAL ~$16.22).

## Affected code

- Renderer: `python/progress_report.py` (`render_phase_detail`, `_phase_round_from_meta`, `_timing_round_windows`, `_round_vendor_cost`, `_fmt_hms`).
- Design entry: `python/review_phase_detail.py` `render_design_review_detail` (reads `timing-ledger.tsv` plus the latest `larch-tokens-*.jsonl`).
- Design timing writer: `python/plan_review.py` `record_plan_review_round_timing` (CLI `plan-review record-round-timing`).
- Canonical timing writer: `python/timing.py` `TimingLedger.record_round` (CLI `timing record-round`).

## Root cause

Two compounding defects.

**1. The normal design plan-review loop never records per-round timing.**

- The only runtime caller of `plan-review record-round-timing` is `skills/design/scripts/design-step3-mav.sh` (the MainAgent 0-judge fallback path).
- The normal loop (`python/plan_review.py`, `python/plan_review_round.py`) records no per-round timing window. The #5393 run took the normal path (`NEXT_ACTION=step3b`), so no design `round` rows were written.
- `_timing_round_windows` then returns `None` for every round; `seconds` is `None`, and `_fmt_hms(None)` renders `—`.

**2. Even when timing is recorded (MAV path), the row format is wrong.**

- The renderer requires the canonical `v1` round row produced by `python/timing.py` `TimingLedger.record_round`: `v1 | round | ts | <skill=col3> | step | <round_n=col5> | <start=col6> | <end=col7> | ...` (13 columns). `_timing_round_windows` gates on `cols[0] == "v1"`, `cols[1] == "round"`, and `len(cols) >= 8`.
- But `record_plan_review_round_timing` writes a bespoke 6-column row: `<start> | <end> | design | round | "design Step 3 — plan review" | round-N`.
- That row fails the `cols[0] == "v1"` / `cols[1] == "round"` / 8-column gate, so it is dropped even on the MAV path. It also puts the round number as `round-N` rather than the bare `N` the reader matches.

Contrast: `/implement` works because `python/review_and_fix.py` `record_round_timing` is called inside the implement loop and delegates to the canonical `python/cli.py timing record-round`, producing reader-compatible rows.

## Why Cost is also empty

Per-round cost is coupled to the per-round time window. `_round_vendor_cost(token_ledger, start_s, end_s)` returns `—` immediately when `start_s` or `end_s` is `None` (`python/progress_report.py`). Those come from the same missing `table_window`. So a missing or malformed timing window breaks Cost as well, even though the token ledger (`larch-tokens-*.jsonl`) holds the per-vendor token data and the run-level cost computed correctly. Fixing the timing window fixes both columns.

## Suggested fix

**Fix 1 (primary): record per-round timing in the normal design loop, using the canonical writer.**

- In the design plan-review loop (`python/plan_review.py` / `python/plan_review_round.py`), capture each round's start and end wall-clock and record the round through the canonical `TimingLedger.record_round(skill="design", step="Step 3 — plan review", round_n=N, start_s=..., end_s=...)` (equivalently shell out to `python/cli.py timing record-round --skill design ...`), mirroring `python/review_and_fix.py` `record_round_timing`.

**Fix 2 (correctness): make the design round-timing writer canonical.**

- Replace the body of `record_plan_review_round_timing` (`python/plan_review.py`) to delegate to `TimingLedger.record_round` (canonical 13-column `v1` row) instead of writing the bespoke 6-column string. This keeps the `plan-review record-round-timing` CLI surface and the `design-step3-mav.sh` callsite intact, and makes MAV-path rows reader-compatible.
- Alternatively, retire `record_plan_review_round_timing` and have `design-step3-mav.sh` call `python/cli.py timing record-round --skill design ...` directly.

**Validation:**

- Add a design-side regression mirroring the implement coverage in `python/test_review_phase_detail.py`: drive a design round (or invoke the recorder), then assert `render_design_review_detail` yields non-`—` Time and Cost for at least one round.
- Add a unit test asserting `plan-review record-round-timing` output parses through `_timing_round_windows(..., skill="design", round_num=N)` (`cols[0] == "v1"`, `cols[1] == "round"`, `len(cols) >= 8`).
- `.claude/rules/launcher-argv-test-coverage.md` requires same-PR harness updates for `plan-review run` changes (`python/test_plan_review.py`).

## Prevention

The design writer and the renderer drifted: `record_plan_review_round_timing` diverges from the canonical `v1` timing schema in `python/timing.py`. A schema-conformance test that runs every `record_round`-style writer through `_timing_round_windows` would catch this class of mismatch and keep the writers and reader in lockstep.

## Test plan
(no test plan section in plan-file)
