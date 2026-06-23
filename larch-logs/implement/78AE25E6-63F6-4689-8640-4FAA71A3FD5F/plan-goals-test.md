## Goal
Implement issue #5222: [IMPLEMENTING] [BUG] Aggregator rc=2 'block missing reviewer attribution line' not covered by retry loop (sibling gap to #5077).

## Implementation Plan
## Summary

`_validate_aggregate_output` returns `(2, "block missing reviewer attribution line\n")` when a merged FINDING block has no `**Reviewer(s)**:` line. `_apply_aggregate_candidate` maps `validate_rc=2` to a single-shot degrade (line 613–616) rather than to `_VALIDATION_FAILED_RC=4`, so the dispatch loop never retries. The exec-issue recorded is `"findings aggregator: merged output failed validation; leaving findings.md unchanged"`. This is a sibling gap to #5077, which fixed the `_MISSING_REVIEWER_RC` case (reviewers absent from the overall set) but left the per-block missing-attribution-line case on the single-shot path.

## Original report

Aggregator validation rc=2 "block missing reviewer attribution line" not covered by retry loop — sibling gap to #5077.

Observed in run `8C1231A4-E9A1-4992-8D18-F4564FDA990C` (PR #5220, issue #5203). `larch-logs/implement/8C1231A4-E9A1-4992-8D18-F4564FDA990C/round-1/aggregator-validate.stderr`:
```
block missing reviewer attribution line
```

## Reproduction scenario

1. Run `/implement` on any issue with a multi-reviewer panel where at least one reviewer raises findings.
2. Have the aggregator LLM produce a merged FINDING block that is missing the `**Reviewer(s)**:` line entirely (the LLM omits the attribution header for that block).
3. `_validate_aggregate_output` → `_reviewer_line_slots(block)` returns empty slots → `return 2, "block missing reviewer attribution line\n"`.
4. `_apply_aggregate_candidate`: `validate_rc=2` is not in `(_OOS_ATTRIBUTION_RC, _MISSING_REVIEWER_RC)` → falls through to `if validate_rc != 0: return 2, str(validate_log)`.
5. Dispatch loop: `pipeline_rc=2 != _VALIDATION_FAILED_RC=4` → no retry, immediate degrade.
6. `execution-issues.md` records: `"findings aggregator: merged output failed validation; leaving findings.md unchanged"`.

## Expected behavior

When a FINDING block is missing its `**Reviewer(s)**:` line, the aggregator should retry (up to `_AGGREGATE_VALIDATION_RETRIES=2` additional attempts) with validator feedback, exactly as it already does for `_OOS_ATTRIBUTION_RC` (#4881) and `_MISSING_REVIEWER_RC` (#5077). This is a recoverable LLM slip.

## Observed behavior

The validation failure degrades single-shot with no retry. `findings.md` is left unchanged. The round proceeds with no aggregated findings.

## Root cause analysis

`_validate_aggregate_output` (line 554–555 of `python/review_aggregate.py`) returns bare `rc=2` for a block with no reviewer attribution line. `_apply_aggregate_candidate` (line 613–616) maps all `validate_rc` values other than `0`, `1`, `_OOS_ATTRIBUTION_RC=5`, and `_MISSING_REVIEWER_RC=6` to `(2, validate_log)`, bypassing `_VALIDATION_FAILED_RC=4`. The dispatch loop only retries on `_VALIDATION_FAILED_RC=4`. The fix in #5077 added `_MISSING_REVIEWER_RC` to the retryable set at the `validate_aggregate_output` level but did not create a distinct RC for the per-block missing-attribution-line case.

## Evidence

- `larch-logs/implement/8C1231A4-E9A1-4992-8D18-F4564FDA990C/round-1/aggregator-validate.stderr` contains exactly: `block missing reviewer attribution line`
- `python/review_aggregate.py:554–555`: `if not slots: return 2, "block missing reviewer attribution line\n"`
- `python/review_aggregate.py:609–616`: only `_OOS_ATTRIBUTION_RC` and `_MISSING_REVIEWER_RC` map to `_VALIDATION_FAILED_RC`; `rc=2` falls through to single-shot degrade
- `python/review_aggregate.py:831–832`: `if pipeline_rc == _VALIDATION_FAILED_RC and attempt < max_attempts:` — rc=2 never satisfies this
- `_MISSING_REVIEWER_RC=6` (line 36) was added by #5077 as a distinct RC to enable retry; the per-block case has no analogous distinct RC

## Affected files

- `python/review_aggregate.py` — `_validate_aggregate_output` (line 554–555), `_apply_aggregate_candidate` (line 609–616), RC constants (lines 27–37)
- `python/test_review_aggregate.py` — needs a test asserting retry fires on "block missing reviewer attribution line"

## Suggested fix(es)

Introduce `_MISSING_ATTRIBUTION_RC = 7` (or similar) in `review_aggregate.py`. Have `_validate_aggregate_output` return it instead of `2` at line 555. Add `_MISSING_ATTRIBUTION_RC` to the retryable set in `_apply_aggregate_candidate` alongside `_OOS_ATTRIBUTION_RC` and `_MISSING_REVIEWER_RC`. Add a test in `python/test_review_aggregate.py` asserting that a block missing its reviewer line triggers a retry with validator feedback rather than an immediate degrade.

The `_validation_retry_prompt` already contains generic repair guidance that applies here; check whether it needs a case for `_MISSING_ATTRIBUTION_RC` or whether the existing message suffices.

## Open questions

- Are there other `return 2, ...` branches in `_validate_aggregate_output` that are also recoverable LLM slips and should get distinct retryable RCs (e.g., "output block missing ### FINDING_N: heading", "output block missing - **Severity**: ... line")?
- Should the retry prompt include a `_MISSING_ATTRIBUTION_RC`-specific hint or is the generic "Re-read the raw reviewer findings above and emit a corrected merge" sufficient?

## Test plan
(no test plan section in plan-file)
