## Proposed Design Outline

### Goals
- Fix Bug 1: `stall-recovery.md` Step 3 always passes `--in-memory-stall-tracking` so an in-memory-only `STALL_TRACKING=true` is not silently dropped before it reaches disk.
- Fix Bug 2: `_classify_text` distinguishes a SIGTERM-killed checks child (`checks-child-failed` + a negative/unresolvable `EXIT_CODE`) from a genuine step-3/6 content failure, classifying the former as `transient-infra` instead of `contract-failure`.
- Wire an actual retry path for the Step 3 SIGTERM case by reusing the existing `checks-commit-route-retry` resume hint and its already-documented Step 3 re-invocation.

### Non-goals
- No new bail token at the `checks-commit-route` producer; `dispatch_commit_route.py` stays untouched. Classification inspects `EXIT_CODE` sign on the existing `checks-child-failed` token.
- No new or tighter retry cap; reuse the existing `transient-infra` cap (4 attempts, 5s delay) in `retry_policy()`.
- No automatic retry dispatch for Step 6. The classification fix applies to both steps (accurate `FAILURE_CLASS` either way), but retry dispatch stays Step-3-only, mirroring the existing `checks-leg-abandoned` precedent.

### Approach sketch
- `_classify.py`: thread `exit_code` into `_classify_text` (compute it before the call in both the `classify()` implement-profile path and the generic-profile path); add a guard before the blanket `step in {"3", "6"}` return that matches `bail == "checks-child-failed"` with a negative or unresolvable exit code.
- `_classify.py`: extend `_resume_hint_for`'s existing step-3-only `checks-commit-route-retry` condition to also match the new pattern, without changing its Step-6 exclusion.
- `_tokens.py`: add the new pattern token to `_safe_matched_pattern_value`'s allowlist so `MATCHED_CLASSIFIER_PATTERN` isn't silently rewritten to `redacted`.
- `stall-recovery.md`: Step 3's "Classify" bullet documents always passing `--in-memory-stall-tracking` (bound from the Step 18a gate's `STALL_TRACKING_MEMORY`); item 5's retry-dispatch paragraph documents the new pattern alongside the existing `checks-leg-abandoned` case.

### Surfaces in scope
- `python/larch/state/_classify.py`
- `python/larch/state/_tokens.py`
- `skills/implement/references/stall-recovery.md`
- `python/tests/state/test_stall_recovery.py`

### Open questions
- None.
