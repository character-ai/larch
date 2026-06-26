## Goal
Implement issue #5503: [IMPLEMENTING] [BUG] aggregator preamble_finding_substring stalls Step 5 instead of retrying with validator feedback.

## Implementation Plan
## Summary

When the findings aggregator produces output that contains `FINDING_` references in its preamble but no parseable `### FINDING_N:` blocks, `_validate_aggregate_output` returns `rc=1` with `AGGREGATOR_VALIDATION_FAILED=preamble_finding_substring`. In `_apply_aggregate_candidate`, `validate_rc == 1` is mapped to `return 1` — a **non-retryable** path — bypassing the `_VALIDATION_FAILED_RC=4` retry loop entirely. The aggregator exhausts its retry budget after a single attempt, emits `reason="validation-exhausted"`, and `review_pipeline.py` returns `ReviewCoreStatus.aggregator_validation_exhausted`. `review_and_fix.py` then stalls Step 5 with `stall_tracking=True` and `stall_reason="aggregator-validation-exhausted"`, requiring a full review-loop retry at the orchestrator level.

## Original report

aggregator stall: review aggregator hits aggregator-validation-exhausted (narrow-trigger preamble contradiction after pattern-gated dispatch), stalling Step 5 and requiring a full review-loop retry. Observed in run 77D53A96-5B8B-4F44-8754-25FB9AD3E744 (issue #5473, PR #5490). The exec-issues entry reads: "findings aggregator: validation exhausted (narrow-trigger preamble contradiction after pattern-gated dispatch); leaving round-1/findings.md unchanged."

## Reproduction scenario

1. Run `/implement` on a repo where the aggregator LLM produces output containing `FINDING_N` references (e.g. in a preamble sentence) but no conforming `### FINDING_N:` heading blocks.
2. `_validate_aggregate_output` triggers the `_has_preamble_finding_signal` check at line 541 of `python/review_aggregate.py`, returns `(1, "AGGREGATOR_VALIDATION_FAILED=preamble_finding_substring\n")`.
3. `_apply_aggregate_candidate` maps `validate_rc == 1` → `return 1` (non-retryable), skipping the `_VALIDATION_FAILED_RC=4` re-dispatch loop.
4. Step 5 stalls with `STALL_REASON=aggregator-validation-exhausted`.

The trigger appears to be non-deterministic: run 77D53A96 stalled on the first attempt and succeeded on immediate retry with the same inputs.

## Expected behavior

The `preamble_finding_substring` failure class is a recoverable LLM slip (the model output structure is wrong, but the content is not inherently invalid). Like `_OOS_ATTRIBUTION_RC`, `_MISSING_REVIEWER_RC`, and `_MISSING_ATTRIBUTION_RC`, it should trigger re-dispatch with validator feedback, up to `_validation_retry_budget()` additional attempts.

## Observed behavior

`preamble_finding_substring` (mapped to `validate_rc=1` in `_validate_aggregate_output`) is handled by the `if validate_rc == 1: return 1` branch in `_apply_aggregate_candidate`, which is the **non-retryable** path. The retry loop at line 841 only re-dispatches when `pipeline_rc == _VALIDATION_FAILED_RC == 4`. Since `pipeline_rc=1 != 4`, the loop breaks after one attempt and the aggregator stalls.

## Root cause analysis

In `python/review_aggregate.py`:

- `_validate_aggregate_output` (line 541) returns `(1, "AGGREGATOR_VALIDATION_FAILED=preamble_finding_substring\n")` when it detects FINDING_ references in the preamble but no conforming blocks.
- `_apply_aggregate_candidate` (line 613–614) maps `validate_rc == 1` → `return 1, validate_log` — a non-retryable code.
- The retry loop (line 841) only retries on `_VALIDATION_FAILED_RC = 4`.
- OOS-attribution, missing-reviewer, and missing-attribution slips were explicitly added to the retryable set (issues #4881, #5077, #5222) but `preamble_finding_substring` was not included at the same time.

The fix is to treat `preamble_finding_substring` as a retryable slip — either by changing `_validate_aggregate_output` to return a new rc that `_apply_aggregate_candidate` maps to `_VALIDATION_FAILED_RC`, or by detecting the preamble failure token in `_apply_aggregate_candidate` before the blanket `validate_rc == 1` branch and returning `_VALIDATION_FAILED_RC` instead.

## Evidence

- `python/review_aggregate.py` line 28: `_VALIDATION_FAILED_RC = 4`
- `python/review_aggregate.py` line 541–542: preamble check returns `(1, "AGGREGATOR_VALIDATION_FAILED=preamble_finding_substring\n")`
- `python/review_aggregate.py` lines 613–619: `validate_rc == 1` → non-retryable `return 1`; `_OOS_ATTRIBUTION_RC / _MISSING_REVIEWER_RC / _MISSING_ATTRIBUTION_RC` → retryable `return _VALIDATION_FAILED_RC`
- `python/review_aggregate.py` lines 841–846: retry loop only fires on `pipeline_rc == _VALIDATION_FAILED_RC == 4`
- `python/review_aggregate.py` lines 849–859: `pipeline_rc == 1` → logs "validation exhausted (narrow-trigger preamble contradiction after pattern-gated dispatch)" and emits `reason="validation-exhausted"`
- `python/review_pipeline.py` lines 2297–2327: `REASON=validation-exhausted` → `ReviewCoreStatus.aggregator_validation_exhausted` (rc=2)
- `python/review_and_fix.py` lines 2990–2993: `aggregator-validation-exhausted` → `stall_tracking=True`
- Run exec-issues: "findings aggregator: validation exhausted (narrow-trigger preamble contradiction after pattern-gated dispatch); leaving `<TMPDIR>`/round-1/findings.md unchanged."

## Affected files

- `python/review_aggregate.py` — `_validate_aggregate_output`, `_apply_aggregate_candidate`, retry loop, and post-loop stall logging
- `python/test_review_aggregate.py` — needs a test for preamble_finding_substring triggering retry rather than immediate stall

## Suggested fix(es)

In `_apply_aggregate_candidate`, before the blanket `if validate_rc == 1: return 1` branch, add a check for the preamble token and return `_VALIDATION_FAILED_RC` instead:

```python
if validate_rc == 1:
    if "preamble_finding_substring" in _read_text(Path(validate_err)):
        return _VALIDATION_FAILED_RC, str(validate_log)
    return 1, str(validate_log)
```

Alternatively, dedicate a new rc constant (e.g. `_PREAMBLE_SLIP_RC`) in `_validate_aggregate_output` and add it to the retryable set in `_apply_aggregate_candidate` alongside the existing three.

Add a regression test in `python/test_review_aggregate.py` asserting that aggregator output with `FINDING_` in a preamble but no proper blocks triggers re-dispatch rather than immediate stall.

## Open questions

- Should a `_validation_retry_prompt` tailored to the preamble class be added (analogous to the OOS-attribution guidance added in #4881), or is the generic retry prompt sufficient?
- Are there other `validate_rc == 1` shapes that are similarly recoverable and should be added to the retryable set?

## Test plan
(no test plan section in plan-file)
