### FINDING_1: orchestrator-never.md carve-out must exempt the sanctioned until-waiter under NEVER #3 (and align NEVER #4 / CI-pinned wording)
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-dyn-contract-drift
- **Severity**: important
- **Concern**: The plan adds a premature-notification recovery carve-out aimed at NEVER #4 cross-reference, but `skills/shared/orchestrator-never.md` NEVER #3 still bans ZERO progress-observation tool calls between background launch and `<task-notification>` and explicitly lists **backgrounded watcher loops** among banned shapes. NEVER #4 still bans Bash `for`/`while`/`until` + `sleep` loops without an in-rule exception. Agents that treat `orchestrator-never.md` as the complete contract can therefore still read the sanctioned single re-launched `until` completion waiter as forbidden progress observation (#3), a banned watcher loop (#3), or a banned polling loop (#4), even after a #4-only cross-reference sentence. Paraphrased carve-out text also risks diverging from CI-pinned recovery literals in `AGENTS.md`, `skills/implement/SKILL.md`, and `scripts/test-implement-anti-polling-rule.sh`, reintroducing the drift Item 1 targets.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Extend NEVER #3 with explicit language that exactly one re-launched immediate-background completion waiter (`until <condition>; do sleep N; done`) is not a progress-observation probe and is the sole sanctioned exception to the ZERO-call wait window; keep the existing NEVER #4 cross-reference
  - From Cursor-Pragmatic: In NEVER #3, explicitly exempt exactly one re-launched immediate-background `until` waiter for premature empty `task-notification` recovery; in NEVER #4, add the matching narrow exception so the recovery pattern is not classified as result-file polling
  - From Cursor-dyn-contract-drift: Mirror `skills/implement/SKILL.md:46`: embed the premature-notification exception inside NEVER #3 **How to apply**, explicitly exempting exactly one re-launched Bash `run_in_background` `until` waiter from the backgrounded watcher loops ban; state it applies only after a premature empty `task-notification` while the child is still running
  - From Cursor-dyn-contract-drift: In `orchestrator-never.md` NEVER #3, reuse verbatim the pinned phrase `only sanctioned exception to the Bash polling-loop ban is one re-launched immediate-background completion waiter` plus the exact `one Bash run_in_background task with until <condition>; do sleep N; done` tail already used in `AGENTS.md`


### FINDING_2: rebalance-test-harnesses SKILL.md step 3 still describes pre-pack feasibility
- **Reviewer(s)**: Cursor-Pragmatic, Codex-Generic
- **Severity**: important
- **Concern**: The plan moves `_check_feasibility` to run after `pack()` and replaces the heuristic with a direct post-pack spread estimate, but the operator-facing `.claude/skills/rebalance-test-harnesses/SKILL.md` step 3 still says a warning-only feasibility preflight runs **before packing** on the measured target set. That skill prompt contract (line 14) requires alignment with `scripts/rebalance.md` when behavior changes. Leaving SKILL.md stale would mislead `/rebalance-test-harnesses` operators and contradict the updated script and rebalance.md prose.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add SKILL.md step 3 (and any mirrored prose) to the plan: pack first, then run the post-pack spread warning-only check
  - From Codex-Generic: Add `.claude/skills/rebalance-test-harnesses/SKILL.md` to the plan and minimally update step 3 to say pack first, then run the warning-only packed-spread check over packed shard totals, with orphan timing rows ignored because totals come from packed shard targets




### FINDING_1: stall-recovery.md Step 18a items 4–5 omit submodule-restricted integration
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan’s Item 3 adds a free-standing `submodule-restricted` bullet beside `protected-path`, but `skills/implement/references/stall-recovery.md` Step 18a sub-step 4 still authorizes only the protected-path first-detection warning, and sub-step 5 documents `step2-impl` retry semantics only in the protected-path context. Runtime and `SKILL.md` already treat `FAILURE_CLASS=submodule-restricted` with `RESUME_HINT=none` and no inline Step 2 recovery (`stall-recovery-report.sh`, `stall-recovery-report.md`, `SKILL.md` Step 18a escalation text). An implementer following only the reference doc can add the new bullet elsewhere while items 4–5 stay protected-path-only, leaving operators to infer `step2-impl` applies to submodule stalls or to treat submodule first-detection warnings as out of policy.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Extend sub-step 4 to allow the submodule-restricted first-detection warning and extend sub-step 5 to state FAILURE_CLASS=submodule-restricted uses RESUME_HINT=none with no step2-impl retry (mirror skills/implement/SKILL.md escalation recording and stall-recovery-report.md)
  - From Cursor-Pragmatic: Amend item 4 to explicitly authorize submodule-restricted first-detection warning text alongside protected-path (mirror the protected-path clause), and state RESUME_HINT=none with no step2-impl dispatch; optionally add a matching negation in item 5 parallel to the protected-path subclause



### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: .claude/skills/rebalance-test-harnesses/scripts/rebalance.md:13-20
- **Concern**: Plan updates the Feasibility preflight subsection but does not explicitly require renumbering the High-level behavior steps 5-6. Scenario: After pack-then-check lands, the top-level numbered flow can still say feasibility runs before pack while the Feasibility subsection says the opposite; operators following the wrong section get the old order
- **Proposed resolution**: rebalance.md edit list should include swapping High-level behavior steps 5 and 6 and rewriting step 5 prose to post-pack spread language (not only the Feasibility preflight block)


