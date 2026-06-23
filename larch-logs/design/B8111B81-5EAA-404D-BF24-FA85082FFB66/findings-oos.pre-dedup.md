### OOS_1: settle-rc-dispatch.md still tells Gate B rc=0 to continue to legacy continuation handling
- **Description**: settle-rc-dispatch.md still tells Gate B rc=0 to continue to legacy continuation handling. Scenario: The plan removes the legacy heuristic section from SKILL.md and approval-gates.md, but Step 3.5 still mandates reading settle-rc-dispatch.md, which keeps legacy continuation language beside the new NEXT_ACTION contract.
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/references/settle-rc-dispatch.md:29,41
- **Phase**: design



### OOS_2: plan-review.md still documents STEP3_REVIEW_LOOP_STATUS-only orchestrator handoff
- **Description**: plan-review.md still documents STEP3_REVIEW_LOOP_STATUS-only orchestrator handoff. Scenario: Reference prose says the loop emits STEP3_REVIEW_LOOP_STATUS and returns only for mid-loop bail-out statuses. It does not mention persisted NEXT_ACTION as the post-notification routing directive, so operators reading plan-review.md can miss the new contract.
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/references/plan-review.md:59
- **Phase**: design



### OOS_3: plan-review.md still documents STEP3_REVIEW_LOOP_STATUS-only orchestrator handoff
- **Description**: plan-review.md still documents STEP3_REVIEW_LOOP_STATUS-only orchestrator handoff. Scenario: External reviewer reference prose still describes loop return and cap routing via STEP3_REVIEW_LOOP_STATUS with no NEXT_ACTION table, diverging from the rewritten SKILL.md contract after this change.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/references/plan-review.md:59-61
- **Phase**: design



### OOS_4: `plan-review.md` still documents `STEP3_REVIEW_LOOP_STATUS`-only orchestrator handoff
- **Description**: `plan-review.md` still documents `STEP3_REVIEW_LOOP_STATUS`-only orchestrator handoff. Scenario: After SKILL.md retires the branch matrix, this reference still tells orchestrators to resume via status-only envelopes and single-pass `LOOP_STATUS` values. Operators or harness authors following it can reintroduce status-first routing beside `NEXT_ACTION`.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/references/plan-review.md:59-61
- **Phase**: design



### OOS_5: Gate B settle rc=0 still points at legacy continuation handling
- **Description**: Gate B settle rc=0 still points at legacy continuation handling. Scenario: Settle dispatch tells Gate B rc=0 to continue to loop-mode or legacy continuation handling after the plan deletes the legacy heuristic section (~721-727). Gate B post-apply recovery can follow retired prose instead of `NEXT_ACTION` plus `approval-gates.md` step 10.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/design/references/settle-rc-dispatch.md:29-41
- **Phase**: design



### OOS_6: Gate B prelude still keys legacy `LOOP_STATUS`-only routing when loop envelope is empty
- **Description**: Gate B prelude still keys legacy `LOOP_STATUS`-only routing when loop envelope is empty. Scenario: When `STEP3_REVIEW_LOOP_STATUS` is unset, `design-step35.sh` still writes `.completed/step-3` for `LOOP_STATUS=complete|zero-findings-degraded-panel|main-agent-vote-required`. Harness-only `--mode single` callers can keep sentinel behavior that bypasses the new `NEXT_ACTION` table.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-step35.sh:86-101
- **Phase**: design



