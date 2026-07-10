## Goal
Implement issue #6822: [IMPLEMENTING] [BUG] repair-loop exhaustion emits NEXT_ACTION=stall instead of main-agent-edit;….

## Implementation Plan
## Plan

## Approach

- Route `LOOP_STATUS=exhausted` to the existing main-agent repair path for the same supported sites as `no-changes-stale`: `step3`, `step5-self-review`, `step5-mav`, and `step6`.
- Carry the final post-check redacted failure-log path through the typed repair-loop result. Exhausted-ledger population must use that path, rather than the original `argv --checks-log`, so the main agent receives failure evidence for the tree after the helper’s final edits.
- Do not change stall-recovery classification or resume hints. Once exhaustion is routed to `main-agent-edit`, the main agent gets the required inline repair attempt before any legitimate main-agent-declared stall reaches Step 18. This preserves the existing Step 3/Step 6 contract-failure semantics for those later stalls.
- Preserve the current `no-changes-stale` ledger behavior byte-for-byte. Its ledger continues to use the original resolved `--checks-log`; only exhausted loops use the final in-loop redacted failure log.
- Keep unsupported sites, including all ship-pr-ci sites, on their existing `stall` behavior.

## Files to modify/create

### UPDATED: python/larch/implement/checks_run_relevant.py

- Extend the `LoopResult` dataclass with a dedicated optional final-redacted-failure-log carrier, such as `final_redacted_checks_log`.
- Initialize the field as absent for loop outcomes that do not produce a failed post-check redaction.
- In `run_check_fix_loop`, record the path emitted by the final successful post-check failure-log redaction after each failed helper iteration, so the exhausted terminal result carries the most recent redacted failure detail from the final iteration.
- Ensure the exhausted return preserves this field without repurposing existing ledger fields or the original checks-log argument.
- Do not alter iteration limits, redaction behavior, stdout key names, normal exit-code semantics, or non-exhausted loop-result behavior.

### UPDATED: python/larch/implement/checks_lint_fix.py

- Update `_repair_loop_action` so `loop.status == "exhausted"` returns `main-agent-edit` only when `lint_site` belongs to `_NO_CHANGES_STALE_MAIN_AGENT_SITES` and a valid exhausted-path ledger can be populated.
- Retain the existing `no-changes-stale` behavior and ledger source unchanged.
- Add a narrow exhausted-ledger population path, or generalize the helper with status-specific log selection:
  - For `no-changes-stale`, retain the current resolved `argv --checks-log` behavior.
  - For `exhausted`, read the dedicated final-redacted-log path from `LoopResult` and resolve and validate it through `resolve_checks_log_path`.
  - Populate the existing ledger fields only after validation succeeds: site, trigger, step, phase, dispatcher, exit code, and `LINT_FIX_LEDGER_FAILURE_DETAIL_LOG`.
  - Preserve `main-agent-required` as the trigger for supported fallback sites.
- If the final exhausted log is absent, invalid, or outside the permitted tmpdir, do not emit a ready ledger and retain the existing `stall` fallback.
- Do not change ship-pr-ci routing, stdout key names, normal exit-code semantics, or behavior for unsupported statuses and sites.

### UPDATED: python/tests/implement/test_checks.py

- Add repair-loop command coverage for exhausted loops at `step3` and `step6`.
- Simulate helper edits followed by failed checks through the iteration cap, producing distinct initial and final redacted failure logs.
- Assert that the typed loop result carries the final redacted failure-log path through the exhausted return.
- Assert for each supported exhausted case:
  - Exit code `0`.
  - `NEXT_ACTION=main-agent-edit`.
  - `LOOP_STATUS=exhausted`.
  - `LINT_FIX_LEDGER_READY=true`.
  - Correct site, step, phase, dispatcher, exit-code, and `main-agent-required` trigger fields.
  - `LINT_FIX_LEDGER_FAILURE_DETAIL_LOG` names the validated final in-loop redacted log rather than the original `--checks-log`.
- Add invalid-final-log coverage proving exhausted supported sites retain `NEXT_ACTION=stall` and do not claim a ready ledger when the carried final path is absent or fails validation.
- Add or extend a ship-pr-ci exhaustion test proving it remains exit code `1`, `NEXT_ACTION=stall`, and has no ready ledger.
- Retain the existing `no-changes-stale` assertions unchanged to guard its current output and initial-log ledger behavior.

### UPDATED: skills/implement/references/checks-repair-loop.md

- Change the repeat condition that currently names only `continue` and `stall` so it also names `main-agent-edit`.
- Clarify that supported-site exhaustion enters the existing main-agent edit branch with a ledger pointing to the final repair-loop failure log; the main agent applies inline repairs and reruns the pinned composite launcher.
- Add a normative diagnosis rule for `NEXT_ACTION=main-agent-edit` when `LOOP_STATUS=exhausted` and `LINT_FIX_LEDGER_READY=true`:
  - Read `LINT_FIX_LEDGER_FAILURE_DETAIL_LOG` as the repair diagnosis.
  - Use optional `STDERR_TAIL_PATH` and `CODER_LOG_FILE` when present.
  - For this exhausted branch only, these ledger artifacts supersede the earlier composite-digest diagnosis binding, which may describe the pre-helper tree.
- Clarify that helper exhaustion is not itself a final stall decision: a later stall is declared only after the main-agent repair path cannot resolve the checks failure.
- Preserve Step 6 `--force-checks true`, bgjob wait, Step 5 handoff, and terminal stall contracts.

## Edge cases

- `step5` remains outside `_NO_CHANGES_STALE_MAIN_AGENT_SITES`; do not widen supported-site coverage.
- `ship-pr-ci-initial`, `ship-pr-ci-merge`, and `ship-pr-ci-per-job` retain their current stall and needs-user behavior.
- An exhausted loop whose final redacted log is missing, invalid, or out of tmpdir must not emit a ready ledger or claim a main-agent handoff.
- A non-exhausted loop must not accidentally reuse a stale final-redacted-log carrier from an earlier iteration or outcome.
- `no-changes-stale` continues to use its existing ledger source and output.
- Generic lint or test failures that the main agent later declares stalled retain the existing Step 3/Step 6 classifier behavior; this change does not add classifier evidence or retry routing.
- Checks-child termination and unresolved exit-status behavior remain unchanged.

## Failure modes

- Reusing the initial `--checks-log` for exhausted loops would hand the main agent stale failure evidence after helper edits. Use the final carried and validated redacted log only for exhausted-ledger population.
- Storing the final path outside `LoopResult` would leave the routing layer dependent on undocumented dynamic state or an ambiguous source. Use a dedicated typed field with an explicit absent/default state.
- Returning `main-agent-edit` without a valid ledger would leave the orchestrator unable to locate current failure details. Require successful ledger population before changing the action.
- Retaining the pre-loop composite digest as the diagnosis after an exhausted handoff would direct inline edits at stale failures. For the exhausted main-agent-edit branch, require the ledger failure-detail log to supersede that digest.
- Broadening the supported-site set would alter Step 5 or ship-pr-ci contracts. Reuse the existing set without additions.
- Changing stall-recovery classification without a production evidence handoff would create unreachable or undocumented behavior. Keep classifier and resume-hint code unchanged.

## Testing strategy

- Run focused repair-loop tests in `python/tests/implement/test_checks.py`.
- Run Python lint and type checks only for changed Python files, following `docs/linting.md`.
- Verify the repair-loop reference against emitted `NEXT_ACTION`, `LOOP_STATUS`, ledger, final-log, diagnosis-source, and exit-code contracts.
- Confirm regression coverage for supported exhaustion, typed final-log propagation, final-log freshness, invalid final-log fallback, unsupported ship-pr-ci exhaustion, and unchanged `no-changes-stale` behavior.

## Acceptance

- Run focused repair-loop tests in `python/tests/implement/test_checks.py`.
- Run Python lint and type checks only for changed Python files, following `docs/linting.md`.
- Verify the repair-loop reference against emitted `NEXT_ACTION`, `LOOP_STATUS`, ledger, final-log, diagnosis-source, and exit-code contracts.
- Confirm regression coverage for supported exhaustion, typed final-log propagation, final-log freshness, invalid final-log fallback, unsupported ship-pr-ci exhaustion, and unchanged `no-changes-stale` behavior.

diff_lines: 164

## Test plan
(no test plan section in plan-file)
