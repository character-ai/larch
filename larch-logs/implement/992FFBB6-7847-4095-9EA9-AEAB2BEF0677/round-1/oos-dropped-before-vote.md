### OOS_1: [OUT_OF_SCOPE] `clear-stall` does not unlink dead-PID checks markers
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: `clear-stall` clears `ship-pr-state.sh` / `finalize-state.sh` / `session-env.sh` but never unlinks `.bg-wait-active`. Recovery normally relies on `_bg_wait_marker`'s `finally` to unlink; if that unlink is suppressed or skipped while checks actually passed, a dead-PID marker can keep `STALL_TRACKING_ABANDONED_MARKER=true` and re-trigger Step 18a after `CLEARED=true`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: optionally unlink a dead-PID checks marker inside `clear-stall` when `CLEARED=true`, or assert marker absence before emitting `CLEARED=true`. Out of scope: pre-existing `clear-stall` behavior; this PR only amplifies sensitivity to a stale marker.

### OOS_2: [OUT_OF_SCOPE] Other bg-wait sites lack abandoned-marker mapping
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: `_CHECKS_MARKER_STALL_STEPS` covers only `implement-step3-checks` and `implement-step5-self-review`. Other bg-wait sites (`implement-step5-resume`, Step 6 via `step-6-entry.sh`) can leave the same orphan-marker pattern but still classify as `no-stall`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: extend mapping and resume hints if those sites need the same recovery. Out of scope: not part of this Step 3 bug fix.

### OOS_3: [OUT_OF_SCOPE] `SKILL.md` still documents four stall-tracking layers
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: Step 18 prose still says "four `STALL_TRACKING_*` KVs" while `dispatch_step18.py` now emits five (`STALL_TRACKING_ABANDONED_MARKER`). `step18-cleanup.md` was updated; `SKILL.md` was not.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: align SKILL.md with the five-layer contract. Out of scope: doc-only drift; routing uses `NEXT_ACTION=stall-recovery` from the composite, not manual KV counting.

### OOS_4: [OUT_OF_SCOPE] Abandoned `implement-step5-self-review` should retry self-review composite
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: important
- **Concern**: An abandoned `implement-step5-self-review` marker classifies to `RESUME_HINT=step5-review`, but that marker only exists on the `--self-review` path, where recovery should re-invoke `checks-commit-route --checks-site step5-self-review` per `skills/implement/references/self-review.md`, not `step-5-review.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Extend `_resume_hint_for` (or stall-recovery docs) with a self-review-specific retry hint, or map step5-self-review abandonment to the same composite re-entry as Step 3.

### OOS_5: [OUT_OF_SCOPE] Step 6 checks marker not in `_CHECKS_MARKER_STALL_STEPS`
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: `implement-step6-checks` is not in `_CHECKS_MARKER_STALL_STEPS`, so an external kill during Step 6 `checks-commit-route` can still classify as `no-stall` / `unrecoverable`, the same gap this PR closes for Step 3.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add `implement-step6-checks` → `"6"` and a matching resume-hint branch if Step 6 should share this recovery behavior.

### OOS_6: [OUT_OF_SCOPE] Missing test for `any_stall` precedence over abandoned-marker detection
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: No test asserts that an abandoned marker is ignored when `STALL_TRACKING=true` is already set in session/state files (`any_stall` precedence).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add a fixture with both a dead marker and `STALL_TRACKING=true` in `session-env.sh`, asserting normal `_classify_text` routing rather than `checks-leg-abandoned` short-circuit.

