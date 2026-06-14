# write-design-round-meta.sh

Synthesizes renderer-compatible `/design` plan-review round artifacts inside a
single snapshotted round directory.

## Usage

```text
write-design-round-meta.sh --round-dir DIR
```

`DIR` is a round snapshot such as `$DESIGN_TMPDIR/plan-review/round-N/`. The
helper intentionally has no `--design-tmpdir` fallback: count synthesis reads
only round-local `voting-tally.md`, round-local `findings-classification.tsv`,
and round-local `plan-review-slots.ndjson`, so mutable session-root state from a
later round or a retally cannot leak into round-N metadata.

## Outputs

- `round-meta.json` with string tally keys `ACCEPTED_COUNT`, `REJECTED_COUNT`,
  `EXONERATED_COUNT`, `NEUTRAL_COUNT`, `OOS_ACCEPTED_COUNT`, and
  `OOS_REJECTED_COUNT`, plus `summary.panel.total_slot_count`, a collector
  failure string, and a `revise` object (`status` / `tier`) read from
  `round-N/revise/revise.env` when present (both fields are `null` when the
  revise step has not yet run or is absent).
- `panel-manifest.ndjson` with one compact JSON object per non-blank slot record,
  containing only `slot`, `tool`, and `output`.

## Count sources

Primary source is the `## Findings` table in `voting-tally.md`, using the Item
and Result columns. Fallback source is `findings-classification.tsv`, using
`finding_id` and `voting_result`. If both are absent or unusable, the helper
writes zero counts; it never reads `accepted-plan-findings.md`,
`rejected-findings.md`, or session-root tally files.

## Collector failures

When `round-summary.env` contains a positive `COLLECT_FAILURE_COUNT`, the helper
emits one renderer-readable placeholder collector record per failure:
`TOOL=unknown`, `STATUS=FAILED`, and `REVIEWER_FILE=collector-failure-N.txt`.
This lets Review Phase Detail report reviewer-slot failures instead of a false
zero when collection failed before per-reviewer records existed.

## Exit behavior and coverage

Usage errors exit `2`; missing or malformed best-effort inputs exit `0` after
writing the best metadata possible (no exit `1` for absent `plan-review-slots.ndjson`
— the helper writes `total_slot_count: 0` and proceeds). JSON emission uses `jq`
when available and falls back to Python stdlib JSON. Harness coverage is indirect
through `python/test_plan_review.py`,
`python/test_plan_review.py`, and
`scripts/test-render-review-phase-detail.sh`.

## Security OOS holdback semantics

The helper subtracts security-tagged OOS items from `OOS_ACCEPTED_COUNT` and
`OOS_REJECTED_COUNT` after tallying. This holdback is applied to both the
`voting-tally.md` and `findings-classification.tsv` paths via
`_adjust_security_oos_counts`. The results are floored at zero (negative counts
are clamped). Failure modes: `is_security_block` is sourced from
`python/cli.py voting is-security-block`; if that probe fails, the OOS item is silently excluded
from the subtraction (fail-open). Missing or unreadable OOS finding blocks
(`_extract_oos_block` exit 1) are silently skipped — the count is not decremented
for a block that cannot be classified. The `.tmp` sentinel files used during
output generation are cleaned up via a trap on EXIT to avoid leaving stale
`panel-manifest.ndjson.tmp` or `round-meta.json.tmp` files that would trip
`design-log-publish.sh`'s allowlist guard.
