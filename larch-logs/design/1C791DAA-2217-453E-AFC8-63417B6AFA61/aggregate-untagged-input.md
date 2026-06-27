### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/test_design_lifecycle.py:2015-2027
- **Concern**: Launcher-argv smoke test fake misses defer_pause_save kwarg. Scenario: When step2b_drafter_main starts calling the shared postplan helper with defer_pause_save=True, this stub raises TypeError before the argv assertions run.
- **Proposed resolution**: Accept **_kw or add defer_pause_save: bool = False to the stub.

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/test_design_lifecycle.py:1690-1793,1967-2079
- **Concern**: Pause-save tests still stub _call_pause_save as return-only lambdas. Scenario: The new capture gate will require a whole-line PAUSE_OK=true row; a lambda that only returns 11 emits no trusted pause output, so the updated pause-terminal and rc-11 tests will take the failure path or fail outright.
- **Proposed resolution**: Replace the lambda with a fake that prints PAUSE_OK=true and the expected KV rows, or patch design_pause.pause_save_main instead of _call_pause_save.

### FINDING_3:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/test_design_lifecycle.py:1946-1952
- **Concern**: Legacy sentinel acceptance still needs a helper-only retarget. Scenario: The current test shells out with `CLAUDE_PLUGIN_ROOT=""` and expects rc 0. A straight retarget to `step2b_drafter_main` will hit the later plugin-root guard, so the canonicalization assertion never runs.
- **Proposed resolution**: Route this case to `_folded_step2a_sentinel_prep` or a tiny test-visible wrapper around it only. Do not use the full drafter entry.

### FINDING_4:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/design_lifecycle.py
- **Concern**: Inline-retry `DRAFTER_NEXT_ACTION` mapping must not re-read `fallback_used` after postplan apply. Scenario: `_postplan_decide` sets inline retry when `fallback_used != "true"`, then `_apply_postplan_decision` writes `.step2b-postplan-fallback-used` to `true` and touches `.step2b-postplan-inline-retry-pending` before control returns to `step2b_drafter_main`. If the action resolver re-evaluates `fallback_used != "true"` from disk after `_shared_step2b_postplan_body` returns, rc `10` always maps to `postplan-rc10`, skipping the one-shot inline rewrite and routing operators into the validator-failure flow instead.
- **Proposed resolution**: In `step2b_drafter_main`, map rc `10` to `inline-retry` when postplan already scheduled inline retry (for example `.step2b-postplan-inline-retry-pending` exists, `SCOUT_STALE_CLEARED=true` in delegated stdout, or an explicit `inline_retry` flag on `PostplanResult`); otherwise map to `postplan-rc10`. Do not re-read `fallback_used` after apply. Update the inline-retry predicate prose and tests to match.

### FINDING_5:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/design_lifecycle.py:3359-3448
- **Concern**: Shared rc11 pause handling still prints POSTPLAN rows inside _shared_step2b_postplan_body. Scenario: When step2b_drafter_main or step2b_postplan_main prints result.stdout_lines after the shared body returns, rc11 can emit duplicate POSTPLAN_RC=11 / POSTPLAN_STATUS=pause-save rows and violate the new single trusted-row contract.
- **Proposed resolution**: Make _shared_step2b_postplan_body side-effect free for rc11. Return the POSTPLAN rows in stdout_lines, but remove the direct print(...) calls there and let each caller print once after branching.

### FINDING_6:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:31-33
- **Concern**: Pre-drafter pause can bypass the required `feature-description.txt` gate. Scenario: A `.pause-requested` Step 2b run can still return `pause-terminal` and exit 0 even when `feature-description.txt` is missing, which contradicts the plan’s own non-zero exit gate and lets the design flow continue past a failure condition that should abort the run
- **Proposed resolution**: Move `feature-description.txt` validation ahead of the pre-drafter pause branch, or explicitly fail closed before emitting `pause-terminal` when that file is missing
