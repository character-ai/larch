# Review Round 2

- Mode: `diff`
- 1 accepted, 5 rejected (1 neutral)

## Accepted Findings

### FINDING_1: Plan inlining defeats Cursor no-work / fake-clean backstop (work item 3)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-dyn-cursor-degraded-calibration-output.txt
- **Severity**: important
- **Concern**: Work item 3’s no-work backstop is ineffective for Cursor plan-review after work item 1 inlined the full plan. Slots can return a canned `no_issues_found` sentinel without tool calls yet still report thousands of `inputTokens` from prompt ingestion alone, exceed the 64-token floor, and be recorded `STATUS=OK`, recreating #5518 fake-clean behavior. The existing degraded path also requires `outputTokens>1000` AND bytes `<500`, so incident-shaped responses (25–128 bytes, low `outputTokens`) with bare sentinels stay clean. `python/test_launch_review.py` encodes this gap (stub uses `inputTokens: 5000` with a comment to avoid triggering degradation).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Scope the backstop to plan-review: degrade bare sentinels on normalized result-byte count and/or missing sidecar tool-call evidence; do not rely on inputTokens once the plan is inlined.
  - From cursor-specialist-correctness-output.txt: Add result-byte degradation for bare no_issues_found without requiring high outputTokens, per plan work item 3.
  - From codex-specialist-correctness-output.txt: Downgrade bare no-issue Cursor results when tool-call evidence is absent or the response is only the canned sentinel, not just when input work is <=64 tokens.
  - From cursor-specialist-edge-cases-output.txt: Add a plan-review-specific collector/postprocess guard independent of low input work: e.g. degrade bare no_issues_found when result bytes stay in the incident band and/or sidecar shows no tool calls, or do not apply the input-token floor when the prompt already contains the inlined plan.
  - From dyn-dyn-cursor-degraded-calibration-output.txt: For plan-review Cursor slots, add a signal independent of input-token count: e.g. require sidecar tool-call evidence before accepting a bare sentinel, treat bare sentinel plus sub-200-byte `.result` as degraded even when usage is high, or scope a plan-review-specific downgrade that does not rely on the 64-token floor.


