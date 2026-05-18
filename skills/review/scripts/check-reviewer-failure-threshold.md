# check-reviewer-failure-threshold.sh

**Type**: executable script.

**Purpose**: Compute whether the per-round reviewer specialist panel had more than half its intended slots fail. When the failure rate exceeds 50%, `review-core.sh` exits 2 with `REVIEW_CORE_STATUS=panel-failed`, which `review-and-fix.sh` propagates as exit 2 with `REVIEW_AND_FIX_STATUS=panel-failed`. `/implement` Step 5 already maps that to `STALL_TRACKING=true` and skips to Step 16.

## Args

| Flag | Type | Required | Description |
|---|---|---|---|
| `--collector-results-file FILE` | path | yes | The per-slot status records written by `scripts/collect-agent-results.sh` (blank-line-separated; each record has `STATUS=<value>`). |
| `--panel hard\|simple` | enum | yes | The intended panel size: HARD=12, SIMPLE=7. |
| `--launched-slots N` | non-negative int | no | When set, static slots in `[LAUNCHED_SLOTS, INTENDED_SLOTS)` are counted as `never-launched` failures (vendor was unhealthy → slot never dispatched). Callers must pass the count of launched static slots only; dynamic scout slots are excluded from this math. When omitted, only the static-slot records in the collector results file are counted. |

## Output

Emits to FD 3 (`emit_kv`):

| Key | Value |
|---|---|
| `INTENDED_SLOTS` | 12 (HARD) or 7 (SIMPLE) |
| `SUCCEEDED_SLOTS` | count of static-slot records with `STATUS=OK` or `STATUS=cap_hit` |
| `FAILED_SLOTS` | count of static-slot records with `STATUS != OK && STATUS != cap_hit` plus static never-launched slots |
| `COUNTED_SLOTS` | total static-slot record count from the collector file |
| `NOT_SUBSTANTIVE_SLOTS` | count of static-slot records with `STATUS=NOT_SUBSTANTIVE` (subset of `FAILED_SLOTS`; useful for the degraded-panel banner) |
| `THRESHOLD_OK` | `true` when failures ≤ 50% of intended panel size, else `false` |
| `THRESHOLD_REASON` | human-readable explanation when `THRESHOLD_OK=false`; empty otherwise |

## Threshold

> 50% of intended panel size. Implementation: failure threshold is `INTENDED_SLOTS / 2 + 1` (integer division). For HARD (12) this is 7 → fail if `FAILED_SLOTS >= 7`. For SIMPLE (7) this is 4 → fail if `FAILED_SLOTS >= 4`.

## STATUS classification

`STATUS=cap_hit` is a deliberate static slot-skip, NOT a failure. It counts as `SUCCEEDED_SLOTS` for threshold purposes. `STATUS=NOT_SUBSTANTIVE` counts as both `FAILED_SLOTS` AND `NOT_SUBSTANTIVE_SLOTS`; it indicates a reviewer produced narrative-only output without structured findings. Dynamic scout slots are ignored entirely by this script, including fallback basenames such as `dyn-foo-output-phase2.txt`, `dyn-foo-output-phase3.txt`, and `dyn-foo-output-retry.txt`; the threshold answers whether the baseline 12-slot or 7-slot panel failed, not whether optional dynamic slots failed.

## Callers

- `skills/review/scripts/review-core.sh` — invoked after `collect-findings.sh` and before tally emission. When `THRESHOLD_OK=false`, review-core emits `REVIEW_CORE_STATUS=panel-failed` and exits 2.

## Harness

`skills/review/scripts/test-check-reviewer-failure-threshold.sh` covers HARD/SIMPLE boundary cases (exactly 50%, just-over-50%, both-down).
