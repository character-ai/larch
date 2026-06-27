# Review Round 2

- Mode: `diff`
- 3 accepted, 5 rejected (1 neutral)

## Accepted Findings

### FINDING_6: Missing drafter integration test for `postplan-rc11-pause` vs `pause-terminal`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan required `postplan-rc11-pause` when pause appears after the pre-drafter checkpoint, but only a shared-body unit test and a pre-drafter `pause-terminal` test exist. No integration test covers pause between pre-drafter check and shared postplan emit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add `step2b_drafter_main` test creating `.pause-requested` between pre-drafter check and shared postplan; assert `postplan-rc11-pause` not `pause-terminal`.


### FINDING_7: Missing test for retained-terminal rc-11 success path with `PAUSE_OK=true`
- **Reviewer(s)**: codex-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The new retained-terminal rc-11 branch in `step2b_postplan_main` is not exercised on the success path. `test_step2b_postplan_rc_11_pause_save_gates_terminal` only covers `PAUSE_OK=false`, so a regression that makes the terminal fence fall through to exit `1` or emit duplicate `POSTPLAN_RC=11` rows when `PAUSE_OK=true` would slip past CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Add a test that stubs `design_postplan.postplan_emit_main` to return `11`, stubs `_call_pause_save` to print `PAUSE_OK=true`, and asserts `step2b_postplan_main` returns `0` with exactly one `POSTPLAN_RC=11` line.


### FINDING_8: `test_step2b_drafter_rc11_pause_save_gates_action` omits `STEP2B_DRAFTER_WRAPPER_ROWS_BEGIN` assertion
- **Reviewer(s)**: dyn-dyn-pause-gating-output.txt
- **Severity**: important
- **Concern**: The drafter-internal rc-11 pause gate test checks exit code and absence of `DRAFTER_NEXT_ACTION=postplan-rc11-pause` on `PAUSE_OK=false`, but unlike `test_step2b_drafter_pause_before_fallback_seed` it does not assert that `STEP2B_DRAFTER_WRAPPER_ROWS_BEGIN=1` is omitted. That leaves the plan-mandated fail-closed boundary for drafter rc-11 pause only partially pinned; a regression that emitted a trusted action row after a failed pause-save could slip through.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-pause-gating-output.txt: Extend `test_step2b_drafter_rc11_pause_save_gates_action` to assert `("STEP2B_DRAFTER_WRAPPER_ROWS_BEGIN=1" in out) is expected_action` on the failure branch, matching the pre-drafter pause test at `python/test_design_lifecycle.py:1980-1981`.


