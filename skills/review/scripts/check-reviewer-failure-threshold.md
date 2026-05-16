# check-reviewer-failure-threshold.sh

**Type**: executable script.

**Purpose**: Compute whether the per-round reviewer specialist panel had more than half its intended slots fail. When the failure rate exceeds 50%, `review-core.sh` exits 2 with `REVIEW_CORE_STATUS=panel-failed`, which `review-and-fix.sh` propagates as exit 2 with `REVIEW_AND_FIX_STATUS=panel-failed`. `/implement` Step 5 already maps that to `STALL_TRACKING=true` and skips to Step 16.

## Args

| Flag | Type | Required | Description |
|---|---|---|---|
| `--collector-results-file FILE` | path | yes | The per-slot status records written by `scripts/collect-agent-results.sh` (blank-line-separated; each record has `STATUS=<value>`). |
| `--panel hard\|simple` | enum | yes | The intended panel size: HARD=12, SIMPLE=7. |
| `--launched-slots N` | non-negative int | no | When set, slots in `[LAUNCHED_SLOTS, INTENDED_SLOTS)` are counted as `never-launched` failures (vendor was unhealthy → slot never dispatched). When omitted, only the records in the collector results file are counted. |

## Output

Emits to FD 3 (`emit_kv`):

| Key | Value |
|---|---|
| `INTENDED_SLOTS` | 12 (HARD) or 7 (SIMPLE) |
| `SUCCEEDED_SLOTS` | count of records with `STATUS=OK` or `STATUS=cap_hit` |
| `FAILED_SLOTS` | count of records with `STATUS != OK && STATUS != cap_hit` plus never-launched slots |
| `COUNTED_SLOTS` | total record count from the collector file |
| `THRESHOLD_OK` | `true` when failures ≤ 50% of intended panel size, else `false` |
| `THRESHOLD_REASON` | human-readable explanation when `THRESHOLD_OK=false`; empty otherwise |

## Threshold

> 50% of intended panel size. Implementation: failure threshold is `INTENDED_SLOTS / 2 + 1` (integer division). For HARD (12) this is 7 → fail if `FAILED_SLOTS >= 7`. For SIMPLE (7) this is 4 → fail if `FAILED_SLOTS >= 4`.

## STATUS classification

`STATUS=cap_hit` is a deliberate slot-skip (reviewer's budget cap reached; `HEALTHY=true` per `collect-agent-results.md`), NOT a failure. It counts as `SUCCEEDED_SLOTS` for threshold purposes.

## Callers

- `skills/review/scripts/review-core.sh` — invoked after `collect-findings.sh` and before `detect-wholesale-rejection.sh`. When `THRESHOLD_OK=false`, review-core emits `REVIEW_CORE_STATUS=panel-failed` and exits 2.

## Harness

`skills/review/scripts/test-check-reviewer-failure-threshold.sh` covers HARD/SIMPLE boundary cases (exactly 50%, just-over-50%, both-down).
