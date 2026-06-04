### FINDING_1: Decomposition-panel returns lack complete re-entry/sentinel handling
- **Reviewer(s)**: Codex-Arch, Codex-dyn-caller-synchrony
- **Severity**: important
- **Concern**: The retained Step 3 / Step 2b.5 plan-size-trigger and decomposition-panel return paths are underspecified. Refine-return can still short-circuit to Step 3b without a refinement re-entry, and no-split Continue/non-exiting Split returns may fail to write the needed completion sentinel, allowing pause/resume to replay Step 2b/2b.5.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add the minimum SKILL.md/decompose-panel.md/test-design-structure updates for the retained Step 3 LOOP_STATUS=plan-size-trigger Split-path Refine return: route to the intended re-entry point such as Gate A or an explicit pause/refine path, and write continuation sentinels only when actually continuing
  - From Codex-dyn-caller-synchrony: Extend the proposed decompose-panel and rc12/rc13 caller prose from Refine-only to all non-exiting Split returns, including no-split Continue; write/update .completed/step-2b.5 before returning, and keep the initial-site .completed/step-2b rule as planned.


### FINDING_2: Partition handoff can emit plan-size-trigger after failed size check
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Concern**: The partition_requested handoff can set `LOOP_STATUS=plan-size-trigger` without requiring `check-plan-size` rc=0. If rc2/rc3 only warn-and-continue, the loop may incorrectly route to Split/Override after a failed size check.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Gate partition handoff on check-plan-size rc=0 (early return after rc2/rc3 warn path, mirroring Step 2b.5 step 3). Add test-plan-review-loop case: partition_requested=true plus forced rc2/3 must not emit LOOP_STATUS=plan-size-trigger


### FINDING_3: Thin-fence dispatch can silently continue on unexpected rc
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Concern**: The thin-fence rc dispatch does not require a default abort arm, so unexpected statuses from `design-postplan-emit.sh` can fall through and continue silently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Add a mandatory *) arm to every merged fence that prints the rc and aborts, and pin it in scripts/test-design-structure.sh


### FINDING_4: append-tool-failure output can pollute machine-readable loop stdout
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Concern**: The retained `plan-review-loop` rc2/rc3 warning path does not require suppressing `append-tool-failure.sh` output, so `APPENDED=` or `LOG=` lines can leak into the machine-readable loop stream.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Add the same >/dev/null 2>&1 || true suppression required for design-postplan-emit.sh, and test no APPENDED= or LOG= leakage


### FINDING_5: Thin-fence structure test does not pin required output and rc arms
- **Reviewer(s)**: Cursor-dyn-harness-pins
- **Severity**: important
- **Concern**: `assert_thin_fence` is too weak: it can pass even if the merged Step 2b fence drops the displayed stdout merge, omits required rc arms, or retains an obsolete rc 0/1-only mandatory-key gate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-harness-pins: Extend `assert_thin_fence` (or add `assert_postplan_thin_fence`) to require immediate display echo plus `case` arms for 0, 10, 11, 12, 13, 2, and 1 inside each pinned region; add a negative self-test fixture missing an arm

