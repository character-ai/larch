### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1117; skills/design/references/decompose-panel.md:80
- **Concern**: The plan adds a plan-review-loop partition_requested handoff but does not define the retained Step 3 plan-size-trigger Refine-return route. Scenario: With --partition, plan-review-loop can return LOOP_STATUS=plan-size-trigger even when no hard threshold fired; Step 3 then runs Step 2b.5, but if the user picks Refine plan myself in the decomposition panel, the current caller text still says to short-circuit to Step 3b, so the design can advance without giving the user a refinement re-entry
- **Proposed resolution**: Add the minimum SKILL.md/decompose-panel.md/test-design-structure updates for the retained Step 3 LOOP_STATUS=plan-size-trigger Split-path Refine return: route to the intended re-entry point such as Gate A or an explicit pause/refine path, and write continuation sentinels only when actually continuing

### FINDING_2:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/plan-review-loop.sh:600-623
- **Concern**: Partition handoff lacks check-plan-size rc=0 guard. Scenario: Plan adds partition_requested→LOOP_STATUS=plan-size-trigger when no hard trigger, but rc2/rc3 is only warn-and-continue. Step 2b.5 returns before partition/hard branches on rc2/rc3. Loop could still set plan-size-trigger after a failed size check and route to Split/Override incorrectly
- **Proposed resolution**: Gate partition handoff on check-plan-size rc=0 (early return after rc2/rc3 warn path, mirroring Step 2b.5 step 3). Add test-plan-review-loop case: partition_requested=true plus forced rc2/3 must not emit LOOP_STATUS=plan-size-trigger

### FINDING_3:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:51-57
- **Concern**: Thin-fence rc dispatch does not require a default abort arm. Scenario: If design-postplan-emit.sh exits with an unexpected non-listed rc such as 126, 127, or signal-derived status after set +e capture, a case with only the listed arms can fall through and continue silently
- **Proposed resolution**: Add a mandatory *) arm to every merged fence that prints the rc and aborts, and pin it in scripts/test-design-structure.sh

### FINDING_4:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/plan-review-loop.sh:601-618
- **Concern**: Proposed rc2/rc3 warning logging does not require suppressing append-tool-failure output. Scenario: In a retained plan-review-loop check-plan-size rc2/rc3 path, append-tool-failure.sh can emit APPENDED= and LOG= lines into plan-review-loop stdout, polluting the machine-readable loop stream
- **Proposed resolution**: Add the same >/dev/null 2>&1 || true suppression required for design-postplan-emit.sh, and test no APPENDED= or LOG= leakage

### FINDING_5:
- **Reviewer(s)**: Codex-dyn-caller-synchrony
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/decompose-panel.md:119-124; skills/design/SKILL.md:1012-1013
- **Concern**: Merged Split sentinel rule covers Refine-return but misses the no-split Continue return. Scenario: After rc12/rc13 enters the decomposition panel, unanimous no-split lets the operator choose Continue and return to the caller; because the merged path no longer re-enters standalone Step 2b.5, the legacy any non-exiting return sentinel at SKILL.md:1012-1013 is not guaranteed, so pause/resume can replay Step 2b/2b.5
- **Proposed resolution**: Extend the proposed decompose-panel and rc12/rc13 caller prose from Refine-only to all non-exiting Split returns, including no-split Continue; write/update .completed/step-2b.5 before returning, and keep the initial-site .completed/step-2b rule as planned.

### FINDING_6:
- **Reviewer(s)**: Cursor-dyn-harness-pins
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-design-structure.sh:40-87
- **Concern**: `assert_thin_fence` only checks `set +e`, `$?`, and Step-3.6 fat-fence bans — not `echo "$out"` or explicit `case` arms for 0/10/11/12/13/2/1. Scenario: Merged Step 2b can drop stdout-KV merge yet still omit `echo "$_postplan_out"`, skip rc 10–13 arms, or keep the rc 0/1-only mandatory-key gate (`skills/design/SKILL.md:936-940`) while passing thin-fence CI
- **Proposed resolution**: Extend `assert_thin_fence` (or add `assert_postplan_thin_fence`) to require immediate display echo plus `case` arms for 0, 10, 11, 12, 13, 2, and 1 inside each pinned region; add a negative self-test fixture missing an arm
