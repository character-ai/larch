## Decision 1: Scope — review-and-fix only vs. plan-review as well
- **Question**: Does this bug apply to the /design plan-review pipeline in addition to /implement?
- **Resolution**: Fix is scoped to `round_runner.py` only. `plan_review_round.py` (used by /design) has its own voter dispatch and no `_run_round` / `degraded-retry.flag` logic; its degraded handling paths are separate.
- **Source**: codebase

## Decision 2: Detection of "pure under-quorum" vs. other degraded causes
- **Question**: Which signal distinguishes a pure per-item under-quorum from reviewer-slot or voter-slot removal degradation?
- **Resolution**: Three conditions must all hold: (1) `UNDER_QUORUM_COUNT > 0` from `core` dict (tally emits this), (2) `PARSE_FAILED_COUNT == 0` from `core` dict (no voter slot removed due to ≥80% JUDGE_ERROR rate), (3) `FAILED_SLOTS == 0` from `threshold_env` (no reviewer slot failures). If any condition is false, fall through to existing fresh-panel retry.
- **Source**: codebase

## Decision 3: Retry cap for the targeted re-vote path
- **Question**: Should the `degraded-retry.flag` / `degraded-retry.done` single-retry cap apply to the targeted re-vote, or only to the full fresh-panel retry?
- **Resolution**: Issue says "Keep the single-retry cap … and the #5528 attempt-tally preservation." The cap sentinel is used per-attempt-1; the targeted re-vote replaces attempt 2 (full panel) when conditions are met. Use the same `degraded-retry.flag` / `degraded-retry.done` sentinels for the re-vote path so the cap still prevents infinite loops.
- **Source**: codebase + issue body
