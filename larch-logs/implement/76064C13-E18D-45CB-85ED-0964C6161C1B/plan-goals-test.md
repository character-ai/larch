## Goal
Implement issue #5077: [IMPLEMENTING] [BUG] Aggregator missing-reviewer validation failure not covered by retry loop.

## Implementation Plan
## Summary

The findings aggregator fails with `"input reviewers missing from merge output"` (validation rc=2) when an aggregator LLM run omits one or more reviewer slots from all merged finding blocks. This failure does not trigger the existing re-dispatch-with-feedback retry loop; it degrades immediately, leaving `findings.md` unchanged. The retry loop (up to 3 attempts via `_AGGREGATE_VALIDATION_RETRIES=2`) only fires for `_VALIDATION_FAILED_RC`-class failures (currently only OOS-attribution errors). As a result, a single recoverable LLM slip permanently degrades the review round aggregation.

## Original report

aggregator failure (dedup with recently closed issues as well as currently open issues -- it's possible we already fixed this yesterday but the fix was not yet in your version of Larch

## Reproduction scenario

1. Run `/implement` on any issue with a multi-reviewer panel.
2. Have two or more reviewers (e.g. `cursor-specialist-edge-cases`, `cursor-specialist-testing`) raise findings that the aggregator LLM decides to merge into blocks attributed to other reviewers, omitting the original slot names from every `**Reviewer(s)**:` line.
3. Aggregator validation fires: `input reviewers missing from merge output: ['cursor-specialist-edge-cases', 'cursor-specialist-testing']`.
4. `_apply_aggregate_candidate` returns `(2, validate_log)`.
5. The outer dispatch loop in `aggregate_findings` sees `pipeline_rc != _VALIDATION_FAILED_RC`, so `break`s immediately — no re-dispatch, no feedback to LLM.
6. `execution-issues.md` records `"findings aggregator: merged output failed validation; leaving findings.md unchanged"`.

Confirmed in run `EFDE1AEE-3BC4-4FBE-B211-DEBDD03DAF77` (PR #5069, issue #4981):
`larch-logs/implement/EFDE1AEE-3BC4-4FBE-B211-DEBDD03DAF77/round-1/aggregator-validate.stderr`:
```
input reviewers missing from merge output: ['cursor-specialist-edge-cases', 'cursor-specialist-testing']
```

## Expected behavior

When aggregator validation returns `"input reviewers missing from merge output"`, the aggregator re-dispatches up to `_AGGREGATE_VALIDATION_RETRIES` additional times (default 2), feeding the exact validator error back into the prompt via `_validation_retry_prompt`. This is the same behavior already implemented for OOS-attribution failures (issue #4881).

The retry prompt already contains the correct generic repair guidance:
> "Fix exactly the error reported above while preserving every input reviewer slot in the merged output. Re-read the raw reviewer findings above and emit a corrected merge."

## Observed behavior

The "missing reviewers" validation failure (rc=2) bypasses the retry loop. `_apply_aggregate_candidate` returns `(2, path)` and the `aggregate_findings` outer loop hits `break` because `pipeline_rc != _VALIDATION_FAILED_RC`. Zero retries occur; findings are left unchanged.

## Root cause analysis

In `python/review_aggregate.py`, `_validate_aggregate_output` returns `2` for the missing-reviewer check (line 565), and `_apply_aggregate_candidate` forwards that `rc=2` directly (line 628):

```python
if validate_rc != 0:
    # Issue #4881: all other semantic validation failures degrade single-shot rather than
    # re-dispatching with OOS-specific repair guidance that does not match the real error.
    return 2, str(validate_log)
```

The comment references issue #4881, which scoped only the OOS-attribution failure for re-dispatch. The "missing reviewers" failure was grouped with all other rc!=0 cases and excluded from retry at that time. The generic `_validation_retry_prompt` was added (without OOS-specific guidance) but never wired to the missing-reviewer path.

The fix is to return `_VALIDATION_FAILED_RC` instead of `2` for the `"input reviewers missing from merge output"` case, enabling the existing retry loop to cover it. The existing generic retry prompt is already appropriate for this error class.

## Evidence

- `larch-logs/implement/EFDE1AEE-3BC4-4FBE-B211-DEBDD03DAF77/round-1/aggregator-validate.stderr`: `input reviewers missing from merge output: ['cursor-specialist-edge-cases', 'cursor-specialist-testing']`
- `python/review_aggregate.py` line 565: `return 2, f"input reviewers missing from merge output: {missing!r}\n"`
- `python/review_aggregate.py` lines 622-628: only `_OOS_ATTRIBUTION_RC` maps to `_VALIDATION_FAILED_RC`; all other `validate_rc != 0` return `2` immediately
- `python/review_aggregate.py` lines 803-829: retry loop guards on `pipeline_rc == _VALIDATION_FAILED_RC`; `rc=2` breaks immediately
- `_validation_retry_prompt` (lines 697-702) has generic repair guidance that covers the missing-reviewer case
- `/issue` skill dedup already checks open + recently closed issues (90-day window by default via `--closed-window-days`); no separate fix needed there unless the window needs adjustment

## Affected files

- `python/review_aggregate.py` — `_apply_aggregate_candidate`: the missing-reviewer `return 2` on line 628 should return `_VALIDATION_FAILED_RC` so the retry loop in `aggregate_findings` covers it
- `python/test_review_aggregate.py` (if it exists) — add test that missing-reviewer validation triggers re-dispatch with feedback, not immediate degradation

## Suggested fix(es)

In `_apply_aggregate_candidate`, change the missing-reviewer case to return `_VALIDATION_FAILED_RC`:

```python
# Before (line ~628):
if validate_rc != 0:
    return 2, str(validate_log)

# After:
if validate_rc == _OOS_ATTRIBUTION_RC or "input reviewers missing from merge output" in validate_err:
    return _VALIDATION_FAILED_RC, str(validate_log)
if validate_rc != 0:
    return 2, str(validate_log)
```

Alternatively, check `validate_rc == 2` and test whether the error text matches the missing-reviewer pattern. Either approach routes the error through the existing `_validation_retry_prompt` feedback loop.

A cleaner option is to introduce a separate RC constant `_MISSING_REVIEWER_RC` analogous to `_OOS_ATTRIBUTION_RC` so the validator surface is fully enumerated.

## Open questions

- Is the user's note "dedup with recently closed issues as well as currently open issues" referring to a separate issue in the `/issue` skill dedup, or is it background context? The `/issue` skill already checks a 90-day closed-issue window by default; if that window is insufficient, `--closed-window-days` can be increased.
- Should `_AGGREGATE_VALIDATION_RETRIES` be increased for the missing-reviewer case specifically, or is the existing default of 2 retries sufficient?
- Are there other rc=2 cases in `_validate_aggregate_output` (e.g. `"block missing reviewer attribution line"`, `"duplicate merged FINDING id"`) that should also be made retriable?

## Test plan
(no test plan section in plan-file)
