## Decision 1: Bail-token granularity for SIGTERM-killed checks
- **Question**: Should the fix stay confined to the classifier (single `checks-child-failed` bail token, distinguish SIGTERM via `EXIT_CODE` sign), or introduce a new `checks-child-sigterm` bail token at the `checks-commit-route` producer?
- **Resolution**: Keep a single `checks-child-failed` bail token. `_classify_text` distinguishes a signal-killed child from a genuine content failure by inspecting `EXIT_CODE` (negative or unknown), not by a new producer-side token. Change stays confined to `_classify.py` (+ its `MATCHED_CLASSIFIER_PATTERN` allowlist in `_tokens.py`) and `stall-recovery.md`; `dispatch_commit_route.py` is untouched.
- **Source**: user

## Decision 2: Retry cap for the new Step-3 SIGTERM retry path
- **Question**: Reuse the existing global `transient-infra` retry cap (4 attempts, 5s delay), or add a tighter 1-2 attempt cap specific to this SIGTERM path (per the issue's suggested fix #3)?
- **Resolution**: Reuse the existing cap of 4. No change to `retry_policy()`, which keys only on `FAILURE_CLASS` today. Consistent with how `checks-commit-route-retry` already behaves for the existing `checks-leg-abandoned` pattern.
- **Source**: user

## Decision 3: Step 6 retry scope
- **Question**: Step 6 (`checks-commit-route --checks-site step6`, via `step-6-entry.sh --force-checks true`) is structurally susceptible to the identical SIGTERM-misclassification bug as Step 3 (`_run_relevant_checks_for_site` is shared). Should the fix also wire automatic retry for Step 6, or classification-only?
- **Resolution**: Classification-only for Step 6 (correctly reports `transient-infra` instead of the misleading `contract-failure`, improving diagnosability for any filed stall issue), but no automatic retry dispatch. This mirrors existing precedent: `_resume_hint_for`'s current `checks-commit-route-retry` dispatch for the analogous `checks-leg-abandoned` pattern is already gated to `safe_step == "3"` only, deliberately excluding Step 6 today. The new pattern follows the same asymmetry rather than introducing new Step 6 retry-dispatch prose and a `step-6-entry.sh`-specific re-invocation contract.
- **Source**: codebase (existing `_resume_hint_for` step-3-only gating for `checks-leg-abandoned`)
