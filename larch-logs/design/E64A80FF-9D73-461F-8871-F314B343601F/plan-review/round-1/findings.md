### FINDING_1:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-design-structure.sh:272-283
- **Concern**: Plan rewrites approval-gates.md and discussion-rounds.md to call design-postplan-emit.sh but only lists pin updates for 14b10, 14c14c-h, FINDING_21, and 1124-1125 — not 14c14d/e/g/h. Scenario: make test-design-structure fails after prose drops invoke-plan-validator.sh even though the driver still wraps it
- **Proposed resolution**: Add 14c14d/e/g/h to the coupled-pin list: retarget them to design-postplan-emit.sh (and driver-internal EMIT-before-validator order), or drop them only if replaced by stronger driver pins

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:764-794
- **Concern**: Step 2b uses three bash fences each with session-env and design-pause-save prelude; the plan collapses them into one design-postplan-emit call without requiring that prelude. Scenario: Cooperative pause between EMIT snapshot and validator is lost; contradicts locked no behavior change
- **Proposed resolution**: Mandate the same two-line prelude (current-design-env source plus .pause-requested exec) immediately before the single design-postplan-emit invocation in Step 2b and in any new bash fence added for re-emit sites

### FINDING_3:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:764-793
- **Concern**: Step 2b consolidation omits orchestrator prelude and inter-step pause checkpoints. Scenario: Each of the three Step 2b bash fences currently sources `current-design-env-$PPID.sh` and `exec`s `design-pause-save.sh` when `.pause-requested` exists; merging to one `design-postplan-emit.sh` call with only a single prelude loses the two mid-sequence pause gates between EMIT_PLAN, HARD snapshot, and validator
- **Proposed resolution**: In the SKILL.md Step 2b replacement fence, keep the session-env source and pause `exec` lines before the driver call; either call `design-pause-save.sh` inside `design-postplan-emit.sh` before each internal step (emit / snapshot / validate) or document and accept the behavior change

### FINDING_4:
- **Reviewer(s)**: Cursor-dyn-reemit-wiring
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:522 / plan.txt:58-61,102-104
- **Concern**: Gate A re-entry guard omits defects-found orchestration. Scenario: Approach requires every re-emit site to parse driver KVs, route VALIDATE_STATUS=defects-found to the shared AskUserQuestion body, then Step 2b.5; the Gate A optional-trailer paragraph update only swaps inline EMIT/validator for design-postplan-emit.sh and never adds that branch (approval-gates.md and discussion-rounds.md updates do)
- **Proposed resolution**: Extend the Gate A optional-trailer guard edit to mirror Step 2b / Gate B: after the driver call and KV parse, route defects-found to ### Plan command validator failure (shared) with site design discussion-round2 or Gate A as appropriate, then Step 2b.5 on exit 0 otherwise

### FINDING_5:
- **Reviewer(s)**: Cursor-dyn-harness-pin-drift
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-design-structure.sh:270-283
- **Concern**: Structural pin migration omits retiring 14c14d/14c14e/14c14f/14c14g. Scenario: Plan replaces approval-gates.md and discussion-rounds.md steps 7–8 with a single `design-postplan-emit.sh` call (plan.txt:109-120) but only says “14c14c-h → assert … invoke the driver” (plan.txt:131-132); it does not explicitly drop the existing `invoke-plan-validator.sh` and EMIT-before-validator line-order pins at 14c14d–14c14h. After prose swap those greps fail and `make test-design-structure` breaks even if the driver is correct.
- **Proposed resolution**: In the `### UPDATED: scripts/test-design-structure.sh` section, list removal/replacement of 14c14d, 14c14e, 14c14f, and 14c14g (not only the driver-invoke addition) and keep 456/459 as the dedup-ordering pins.
