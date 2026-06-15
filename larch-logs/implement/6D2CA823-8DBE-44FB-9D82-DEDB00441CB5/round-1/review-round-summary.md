# Review Round 1

- Mode: `diff`
- 2 accepted, 5 rejected (0 neutral)

## Accepted Findings

### FINDING_12: **correctness** `skills/implement/SKILL.md:594-602` — Wrapper preflight failure handling is incomplete after folding the two-fence pattern into one launcher. Line 594 says to log and skip loop-status parsing when the wrapper exits non-zero without `STEP5_REVIEW_STATUS`, but the next block still assumes a parseable `STEP5_REVIEW_STATUS` and routes into `Branch on STEP5_REVIEW_STATUS`. The old split layout implicitly gated this: a failing foreground `step-5-entry.sh` (e.g. cap validation at `skills/implement/scripts/step-5-review.sh:44-45`) never reached the review loop. A single combined fence needs an explicit terminal path (e.g. set `STALL_TRACKING=true`, skip to Step 16). **Suggested fix:** After line 594, add mandatory routing for the no-`STEP5_REVIEW_STATUS` case: log to `Warnings`, set `STALL_TRACKING=true`, and skip to Step 16 (or Step 18); forbid falling through to status branching when `STEP5_REVIEW_STATUS` is unset.
- **Reviewer**: dyn-step5-launcher-output.txt
- **Concern**: - **correctness** `skills/implement/SKILL.md:594-602` — Wrapper preflight failure handling is incomplete after folding the two-fence pattern into one launcher. Line 594 says to log and skip loop-status parsing when the wrapper exits non-zero without `STEP5_REVIEW_STATUS`, but the next block still assumes a parseable `STEP5_REVIEW_STATUS` and routes into `Branch on STEP5_REVIEW_STATUS`. The old split layout implicitly gated this: a failing foreground `step-5-entry.sh` (e.g. cap validation at `skills/implement/scripts/step-5-review.sh:44-45`) never reached the review loop. A single combined fence needs an explicit terminal path (e.g. set `STALL_TRACKING=true`, skip to Step 16). **Suggested fix:** After line 594, add mandatory routing for the no-`STEP5_REVIEW_STATUS` case: log to `Warnings`, set `STALL_TRACKING=true`, and skip to Step 16 (or Step 18); forbid falling through to status branching when `STEP5_REVIEW_STATUS` is unset.
- **Suggested revision**: Address the concern above.


### FINDING_6: risk-integration: skills/implement/SKILL.md:594-602
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Preflight failure after step-5-review.sh exits non-zero without STEP5_REVIEW_STATUS is only told to log and skip status branches; no terminal routing is defined. Invalid LARCH_DYNAMIC_ARCHETYPES_MAX (e.g. 9) makes the wrapper exit 2 before exec; orchestrator may proceed toward Step 6 without STEP5_REVIEW_STATUS, skipping the review loop and violating NEVER #4. Add explicit terminal routing: STALL_TRACKING=true, STALL_STEP=5, log Warnings, skip to Step 16; state that Step 6 continuation requires a present STEP5_REVIEW_STATUS.
- **Suggested revision**: Address the concern above.


