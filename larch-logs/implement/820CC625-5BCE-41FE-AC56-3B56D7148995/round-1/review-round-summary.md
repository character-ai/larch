# Review Round 1

- Mode: `diff`
- 7 accepted, 5 rejected (4 neutral)

## Accepted Findings

### FINDING_1: `DRAFTER_NEXT_ACTION=failsafe-missing-rows` documented but never emitted
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-dyn-step2-routing-output.txt, dyn-dyn-skill-contract-output.txt
- **Severity**: important
- **Concern**: `DRAFTER_NEXT_ACTION=failsafe-missing-rows` is documented in `skills/design/SKILL.md`, `skills/design/references/step2b-drafter-failsafe.md`, and the plan, but `step2b_drafter_main` never emits it (`grep` finds zero matches under `python/`). `_emit_drafter_next_action` covers nine other tokens only. On a future exit-0 path where postplan completes non-fatally but no trusted action row is emitted, the orchestrator fail-closes instead of entering the retained terminal postplan failsafe recovery described in the skill contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add a final exit-0 safety net emitting failsafe-missing-rows, or teach SKILL to bind absent/unknown directives to that token.
  - From cursor-specialist-edge-cases-output.txt: Add a terminal safety net that emits failsafe-missing-rows on the plan-specified zero-exit branch and add pytest coverage.
  - From cursor-specialist-testing-output.txt: Add a resolver branch that emits failsafe-missing-rows on zero-exit degraded postplan output and a lifecycle test asserting the token.
  - From dyn-dyn-step2-routing-output.txt: Add a resolver branch (or end-of-function guard) in `step2b_drafter_main` that emits `DRAFTER_NEXT_ACTION=failsafe-missing-rows` on exit 0 when structural/postplan success cannot be mapped to a normal token, and add the planned pytest coverage for that token.
  - From dyn-dyn-skill-contract-output.txt: Add a terminal resolver in `step2b_drafter_main` that emits `failsafe-missing-rows` on exit 0 when postplan completed but no action was chosen (or centralize emission so every exit-0 return goes through one function that cannot return without an action), plus a lifecycle test that stubs postplan into that state.


### FINDING_3: Plan-mandated Step 2b routing and failsafe pytest coverage missing
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan-mandated tests for `failsafe-missing-rows`, `resume@2a` never calling `design step2a`, brainstorm step-1d.5 skip, drafter conflict refusal without action rows, inline-fallback, dirty-tree-recovery, pre-drafter `PAUSE_OK=false`, and each `DRAFTER_NEXT_ACTION` branch are missing or only covered at helper/structure-test depth. Regressions in failsafe routing, resume semantics, or newly introduced drafter branches could ship undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add the missing pytest cases from the plan testing section.
  - From cursor-specialist-testing-output.txt: Add focused `step2b_drafter_main` and `_folded_step2a_sentinel_prep` tests asserting each missing token and no `DRAFTER_STATUS=` rows.


### FINDING_5: Stale `.step2b-postplan-inline-retry-pending` can spuriously trigger inline-retry
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `_drafter_inline_retry_scheduled` honors a stale `.step2b-postplan-inline-retry-pending` file that pre-launch cleanup does not clear. After pause/resume, a fresh drafter pass with postplan rc 10 may spuriously emit inline-retry instead of following the normal postplan-rc10 path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Clear pending on drafter pre-launch unless an active retry is in flight, or gate only on inline_retry_scheduled from the current postplan result.


### FINDING_9: rc-11 pause-save paths lack end-to-end and fail-closed test coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt, dyn-dyn-pause-gating-output.txt
- **Severity**: important
- **Concern**: Terminal retained postplan rc-11 integration is only tested with `PAUSE_OK=true` and pre-emit `.pause-requested`, not post-emit emit rc 11 through `step2b_postplan_main`. There is no regression test that `PAUSE_OK=false` (or missing `PAUSE_OK`) returns non-zero, emits a single `POSTPLAN_RC=11`, and prevents the retained fence from appearing successful. A bug reintroducing fatal exit 1 or duplicate `POSTPLAN_RC=11` rows on post-emit pause would not be caught.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add step2b_postplan_main test with postplan_emit_main returning 11 and assert pause-save semantics and single POSTPLAN_RC=11 print.
  - From codex-specialist-testing-output.txt: Add a full step2b_postplan_main integration test that makes postplan_emit_main return 11 and asserts the pause-save return path and single POSTPLAN emission.
  - From dyn-dyn-pause-gating-output.txt: Add `test_step2b_postplan_rc_11_pause_save_gates_terminal` with a fake `_call_pause_save` emitting `PAUSE_OK=false`, asserting exit `1`, single `POSTPLAN_RC=11` print, and no false success.


### FINDING_10: Pre-drafter `PAUSE_OK=false` fail-closed boundary untested
- **Reviewer(s)**: dyn-dyn-pause-gating-output.txt
- **Severity**: important
- **Concern**: Pre-drafter `DRAFTER_NEXT_ACTION=pause-terminal` is only tested on the `PAUSE_OK=true` happy path. There is no regression test that `PAUSE_OK=false` (or missing `PAUSE_OK`) exits non-zero and omits `STEP2B_DRAFTER_WRAPPER_ROWS_BEGIN` / `DRAFTER_NEXT_ACTION`, which the plan lists as a required fail-closed boundary for pre-drafter pause.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-pause-gating-output.txt: Parametrize `test_step2b_drafter_pause_before_fallback_seed` (or add a sibling) with `PAUSE_OK=false` and assert exit `1`, no trusted action row, and captured pause diagnostics still printed.


### FINDING_11: rc12/rc13 drafter sidecar cleanup path untested
- **Reviewer(s)**: codex-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The rc12/rc13 sidecar cleanup path in `step2b_drafter_main` is untested. A stale `.drafter-next-action-rc12.txt` or `.drafter-next-action-rc13.txt` could leak the prior run's split/partition prompt into the next `/design` invocation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Add a cleanup regression test that seeds both sidecars, reruns step2b_drafter_main, and asserts both files are removed before new draft logic runs.


### FINDING_13: Step 1d.7/1e breadcrumbs still say "proceed to Step 2a" after fold
- **Reviewer(s)**: dyn-dyn-skill-contract-output.txt
- **Severity**: important
- **Concern**: Step 1d.7 and Step 1e still say "proceed to Step 2a," while Step 2a is now prose-only and explicitly requires continuing in the same turn to the Step 2b drafter fence. That reintroduces a step boundary the fold was meant to remove and conflicts with the anti-halt chain (`2a(folded)→2b`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-skill-contract-output.txt: Reword those breadcrumbs to "proceed to folded Step 2a / Step 2b drafter in the same turn" and point at the `design-step2b-drafter.sh` fence, matching the `resume@2a` carve-out at line 228.


