### OOS_1: [OUT_OF_SCOPE] Setup failures write handoff rc before marker is armed
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: latent
- **Concern**: Setup failures after the EXIT trap is set but before the marker is armed still write `.step-8-ship-handoff.rc` (e.g. exit code `2`). That predates this change; SKILL.md already requires halting when json is absent. Out of scope because it is not introduced by this diff.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_2: [OUT_OF_SCOPE] Step 8 clamp deny reuses misleading “terminal-sentinel” message
- **Reviewer(s)**: cursor-specialist-correctness, dyn-dyn-bg-wait-hooks
- **Severity**: nit
- **Concern**: `step8_handoff_probe_clamp` / `json_deny_probe` still says “terminal-sentinel” when denying clamped Step 8 rc probes. Misleading operator text only; behavior is correct. Pre-existing message reused for Step 8; a Step 8–specific deny message would be clearer.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_3: [OUT_OF_SCOPE] Foreground stale-handoff clear is prompt-only, not mechanically enforced
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: Foreground stale-handoff clear before `run_in_background` is not mechanically enforced in shell/Python (by design: fence-shape lint). Stale-handoff protection on relaunch depends on a separate foreground orchestrator `rm` before every `run_in_background` launch. Residual risk if the orchestrator skips it; mitigated by docs/tests and wrapper entry clear. Accepted design in the plan; operational, not a hook bug.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_4: [OUT_OF_SCOPE] Step 8 recovery classifier accepts only `test -f`, not `[ -f … ]`
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: The Step 8 recovery classifier accepts only `test -f`, not `[ -f … ]`, while `/design` allows both. An orchestrator that copies the design bracket form would hit the generic `$IMPLEMENT_TMPDIR` deny path during ship-pr. SKILL.md, AGENTS.md, and harness literals all pin `test -f`; this is an intentional narrow matcher, not a plan gap.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_5: [OUT_OF_SCOPE] AGENTS.md lint trim removed unrelated escalation guidance
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: The lint-driven trim removed the “Subagents spend 15k–25k tokens…” escalation guidance unrelated to this feature. Collateral from the 12k-char lint fix, not introduced by the bg-wait logic.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_6: [OUT_OF_SCOPE] Vacuous “setup failure removes bg-wait marker” test assertion
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: The `setup failure removes bg-wait marker` assertion is vacuous: the marker is armed only after `require_value` (lines 89–109), so a missing `BRANCH_NAME` failure never creates one. The test passes without exercising marker cleanup.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Either move marker arming earlier (if desired) or rename/retarget the test to paths that actually arm then fail (stale-python / failing-ship cases already cover this).

### OOS_7: [OUT_OF_SCOPE] Relaunch regression test only checks isolated `rm -f`
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: The “relaunch regression” only checks that a standalone `rm -f` deletes pre-seeded sidecars; it does not run a second wrapper launch or hook probe after simulating orchestrator foreground-clear → relaunch. Wrapper entry cleanup is covered by the main dynamic test, but the plan’s full relaunch sequence is not end-to-end locked.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_8: [OUT_OF_SCOPE] AGENTS.md pins Step 8 probe but not hook-clamp clause
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: AGENTS.md pins the Step 8 `test -f` probe but not the `hook-allowed … clamped` clause that also lives in AGENTS (line 86). SKILL and `orchestrator-never.md` are pinned; AGENTS hook-clamp text could drift without CI failure.
- **Suggested revisions (informational for voters; coder decides)**:

