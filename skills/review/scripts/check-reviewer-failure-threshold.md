# check-reviewer-failure-threshold.sh

**Type**: executable script.

**Purpose**: Compute whether the per-round reviewer specialist panel had more than half its intended static slots fail. When the failure rate exceeds 50%, `review-core.sh` exits 2 with `REVIEW_CORE_STATUS=panel-failed`, which `review-and-fix.sh` propagates as exit 2 with `REVIEW_AND_FIX_STATUS=panel-failed`.

## Args

| Flag | Type | Required | Description |
|---|---|---|---|
| `--collector-results-file FILE` | path | yes | The per-slot status records written by `scripts/collect-agent-results.sh` (blank-line-separated; each record has `STATUS=<value>`). |
| `--panel hard\|simple` | enum | yes | Panel shape label. Both shapes use the caller-supplied static denominator. |
| `--intended-slots N` | non-negative int | no | Static slot denominator. Default is `4` for single-vendor/back-compat callers; both-vendor review panels pass `8`. |
| `--launched-slots N` | non-negative int | no | When set, static slots in `[LAUNCHED_SLOTS, INTENDED_SLOTS)` are counted as `never-launched` failures unless dropped-slot accounting is already present. Dynamic scout slots are excluded. |
| `--dropped-slots-file FILE` | path | no | TSV from `dispatch-with-waterfall.sh --no-fallback` (`slot<TAB>tool<TAB>reason<TAB>snippet`). Static dropped rows count as failures; `dyn-*` rows are excluded. |
| `--round-num N` | positive int | no | Round label for diagnostics; default `1`. |

## Output

Emits to FD 3 (`emit_kv`):

| Key | Value |
|---|---|
| `INTENDED_SLOTS` | caller-supplied static denominator (`4` default; commonly `8` when both vendors are available) |
| `SUCCEEDED_SLOTS` | count of static-slot records with `STATUS=OK` or `STATUS=cap_hit` |
| `FAILED_SLOTS` | count of static-slot records with `STATUS != OK && STATUS != cap_hit`, plus dropped static rows and applicable never-launched slots |
| `COUNTED_SLOTS` | total static-slot record count from the collector file |
| `NOT_SUBSTANTIVE_SLOTS` | count of static-slot records with `STATUS=NOT_SUBSTANTIVE` (subset of `FAILED_SLOTS`; useful for the degraded-panel banner) |
| `DROPPED_STATIC_SLOTS` | dropped no-fallback static rows counted from `--dropped-slots-file` |
| `THRESHOLD_OK` | `true` when failures ≤ 50% of intended panel size, else `false` |
| `THRESHOLD_REASON` | human-readable explanation when `THRESHOLD_OK=false`; empty otherwise |

## Threshold

> 50% of intended panel size. Implementation: failure threshold is `INTENDED_SLOTS / 2 + 1` (integer division). For 4 slots this is 3; for 8 slots this is 5.

## STATUS classification

`STATUS=cap_hit` is a deliberate static slot-skip, NOT a failure. It counts as `SUCCEEDED_SLOTS` for threshold purposes. `STATUS=NOT_SUBSTANTIVE` counts as both `FAILED_SLOTS` AND `NOT_SUBSTANTIVE_SLOTS`; it indicates a reviewer produced narrative-only output without structured findings. Dynamic scout slots are ignored entirely by this script, including Cursor and Codex dynamic basenames such as `dyn-foo-output.txt`, `dyn-foo-codex-output.txt`, and their phase/retry variants. The threshold answers whether the static specialist panel failed, not whether optional dynamic slots failed.

## Callers

- `skills/review/scripts/review-core.sh` — invoked after `collect-findings.sh` and before tally emission. When `THRESHOLD_OK=false`, review-core emits `REVIEW_CORE_STATUS=panel-failed` and exits 2.

## Harness

`skills/review/scripts/test-check-reviewer-failure-threshold.sh` covers 4-slot and 8-slot boundary cases, dropped-static accounting, and dynamic Codex-twin exclusion.
