### FINDING_1: Harness pins 14c14d–h not migrated with `design-postplan-emit.sh` prose swap
- **Reviewer(s)**: Cursor-Edge, Cursor-dyn-harness-pin-drift
- **Severity**: important
- **Concern**: The plan rewrites `approval-gates.md` and `discussion-rounds.md` to call `design-postplan-emit.sh` but only couples pin updates to 14b10, 14c14c-h, FINDING_21, and 1124–1125—not explicit removal/replacement of 14c14d, 14c14e, 14c14f, 14c14g, and 14c14h. Those harness lines still grep for `invoke-plan-validator.sh`, EMIT-before-validator ordering, and per-file EMIT pins. After the prose swap, `make test-design-structure` fails even if the driver wiring is correct.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Add 14c14d/e/g/h to the coupled-pin list: retarget them to design-postplan-emit.sh (and driver-internal EMIT-before-validator order), or drop them only if replaced by stronger driver pins
  - From Cursor-dyn-harness-pin-drift: In the `### UPDATED: scripts/test-design-structure.sh` section, list removal/replacement of 14c14d, 14c14e, 14c14f, and 14c14g (not only the driver-invoke addition) and keep 456/459 as the dedup-ordering pins.


### FINDING_2: Step 2b consolidation drops session-env prelude and inter-step pause gates
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: Step 2b currently uses three bash fences, each with the two-line orchestrator prelude (`current-design-env-$PPID.sh` source and `design-pause-save.sh` exec when `.pause-requested` exists) around EMIT_PLAN, HARD snapshot, and validator. The plan collapses them into a single `design-postplan-emit.sh` call without requiring that prelude or equivalent pause checkpoints between internal emit / snapshot / validate steps. That loses cooperative pause behavior and contradicts a locked no-behavior-change intent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Mandate the same two-line prelude (current-design-env source plus .pause-requested exec) immediately before the single design-postplan-emit invocation in Step 2b and in any new bash fence added for re-emit sites
  - From Cursor-Pragmatic: In the SKILL.md Step 2b replacement fence, keep the session-env source and pause `exec` lines before the driver call; either call `design-pause-save.sh` inside `design-postplan-emit.sh` before each internal step (emit / snapshot / validate) or document and accept the behavior change


### FINDING_3: Gate A optional-trailer guard omits `defects-found` orchestration
- **Reviewer(s)**: Cursor-dyn-reemit-wiring
- **Severity**: important
- **Concern**: The approach requires every re-emit site to parse driver KVs and route `VALIDATE_STATUS=defects-found` to the shared AskUserQuestion body, then Step 2b.5 on exit 0. The Gate A optional-trailer guard edit only swaps inline EMIT/validator for `design-postplan-emit.sh` and never adds that branch, while `approval-gates.md` and `discussion-rounds.md` updates do.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-reemit-wiring: Extend the Gate A optional-trailer guard edit to mirror Step 2b / Gate B: after the driver call and KV parse, route defects-found to ### Plan command validator failure (shared) with site design discussion-round2 or Gate A as appropriate, then Step 2b.5 on exit 0 otherwise

