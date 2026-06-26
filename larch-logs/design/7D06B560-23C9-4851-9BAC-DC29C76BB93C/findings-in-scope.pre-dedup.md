### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:29
- **Concern**: Approach preserved-delta list omits the `/design`-only visible-output anti-halt trigger. Scenario: The plan tells implementers to replace generic anti-halt prose with `→ skills/shared/subskill-invocation.md#anti-halt` and to keep only deltas listed in Approach (Immediate-background, step chain, Gate re-entries, etc.). It never lists `after every visible output (plans, voting tallies, skip breadcrumbs), IMMEDIATELY continue`, and `test-design-structure.sh` adds no pin for it. Shared `#anti-halt` treats visible outputs as non-terminal artifacts but does not mandate immediate continuation right after a plan print, voting tally, or skip breadcrumb the way today's always-loaded line does. Following the plan literally can restore halts after Step 2b plan output or Step 3 tallies while still passing the new binding-dedup harness checks.
- **Proposed resolution**: Add the visible-output continuation trigger to Approach preserved deltas and the SKILL.md preamble revise bullets (keep it inline next to the `#anti-halt` cite, matching `/implement`'s pattern of local deltas plus shared anchor); add a `contains` regression in `scripts/test-design-structure.sh` for the contract token (for example `after every visible output`).



### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:28-31
- **Concern**: Approach preserved-delta list omits the always-loaded visible-output anti-halt trigger while binding implementers to keep only listed `/design` deltas. Scenario: Current preamble requires continuation after every visible output (plans, voting tallies, skip breadcrumbs). The plan replaces generic continuation with `→ skills/shared/subskill-invocation.md#anti-halt` and line 31 limits preservation to the Approach bullet list, which does not include visible-output continuation. Shared `#anti-halt` puts that rule only in the narrative paragraph, not the canonical banner orchestrators copy. Implementers can drop the trigger from the always-loaded stub and restore halts after Step 2b plan prints, Step 3 voting tallies, and skip breadcrumbs.
- **Proposed resolution**: Add `after every visible output (plans, voting tallies, skip breadcrumbs)` to the Approach preserved-delta list and the SKILL.md preamble edit bullets. Pin the literal in `scripts/test-design-structure.sh`.



### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:32-38
- **Concern**: Planned recap-ban stub weakens the operative `_publish_rc` and cancellation file gates. Scenario: The live preamble bans recap only after Step 5c returns with `_publish_rc` in {0,1,3} or after cancellation writes a non-empty summary file. The plan replaces that with vague timing (`no free-form recap after Step 5c or cancellation final-summary render`). New harness checks assert recap/no-cost tokens but not the `_publish_rc` gate. Agents may recap too early, miss the `_publish_rc`=1 plan-block-write path, or treat empty cancellation renders as recap-ban boundaries.
- **Proposed resolution**: Preserve the operative trigger verbatim in the always-loaded stub (Step 5c `_publish_rc` 0/1/3 plus cancellation non-empty summary file). Add a `test-design-structure.sh` grep for that trigger alongside the render-exit carve-out pin. ### 1. Visible-output anti-halt missing from preserved deltas (correctness) The plan’s Approach section (lines 9–16) is the binding list for what stays inline when generic prose moves to `subskill-invocation.md#anti-halt`. It omits **after every visible output (plans, voting tallies, skip breadcrumbs)**, which is load-bearing in the current preamble at `skills/design/SKILL.md:29` and is not in the shared canonical banner at `skills/shared/subskill-invocation.md:98`. Pointing at `#anti-halt` does not keep this rule always-loaded. The issue’s own failure mode warns against moving safety rules into lazy-read-only context. Round-2 neutral FINDING_6 is still open: the plan now explicitly enumerates preserved deltas without visible output, which increases regression risk. ### 2. Recap-ban trigger weakened vs operative contract (correctness) The plan’s SKILL.md edit (lines 32–33) replaces a precise gate with softer wording. The operative contract at `skills/design/SKILL.md:29` ties recap prohibition to `_publish_rc` values and a non-empty cancellation summary file. Planned harness work pins render-exit and generic no-recap tokens but not this trigger. Round-2 neutral FINDING_2 on preamble recap timing remains unresolved in the plan text. **Not re-raised (already addressed in current plan):** round-1 accepted `test-render-cost-line-callsites.sh` retargeting (plan lines 94–125); round-2 accepted render-exit carve-out at preamble and Step 5c item 5 (lines 18–19, 55–58, 123).



### FINDING_4:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:29
- **Concern**: Approach preserved-delta list omits the always-loaded visible-output anti-halt trigger. Scenario: Current preamble requires continuation after every visible output (plans, voting tallies, skip breadcrumbs), not only after Bash helpers. The plan replaces generic prose with a cite to subskill-invocation.md#anti-halt while binding implementers to Approach deltas only. Shared #anti-halt names visible outputs as intermediate artifacts but does not require IMMEDIATELY continue after each one; /design prints plans and tallies inline. Over-trimming restores halts after Step 2b plan prints, Step 3 voting tallies, and skip breadcrumbs.
- **Proposed resolution**: Add after every visible output (plans, voting tallies, skip breadcrumbs), IMMEDIATELY continue to the preserved-delta list, the SKILL.md preamble revision bullets, and a test-design-structure.sh grep pin for that phrase (or an equivalent literal token).



### FINDING_5:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:29-33
- **Concern**: Recap-ban timing weakens as Step 5d detailed trigger is collapsed to a preamble back-reference. Scenario: Current preamble bans recap only after Step 5c driver return with _publish_rc in {0,1,3} or after cancellation final-summary with a non-empty file. The plan replaces that with no free-form recap after Step 5c or cancellation final-summary render and collapses Step 5d to cite the preamble only, removing the Step 5d backup that ties the ban to driver refresh plus mandatory Step 5c item 5 emit. Agents may treat after Step 5c as after all of Step 5 (too late) or emit recap between driver return and item 5 emit (before mandatory marker-first body).
- **Proposed resolution**: Keep the operative driver-return trigger in the always-loaded preamble stub (_publish_rc 0, 1, or 3 plus cancellation non-empty summary file) or an equivalent shortened token, and pin it in test-design-structure.sh alongside the existing no-recap grep.



### FINDING_6:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:9-16
- **Concern**: Approach preserved-delta list omits the visible-output anti-halt trigger (`after every visible output (plans, voting tallies, skip breadcrumbs)`), which shared `#anti-halt` does not pin in its canonical banner. Scenario: Implementer replaces generic anti-halt prose with `→ subskill-invocation.md#anti-halt` plus only the listed deltas; orchestrators halt after printing implementation plans, voting tallies, or skip breadcrumbs because neither the shared anchor nor planned harness pins cover that trigger
- **Proposed resolution**: Add visible-output continuation to Approach preserved deltas and the always-loaded preamble stub; add a matching `test-design-structure.sh` grep pin



### FINDING_7:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:59-61
- **Concern**: Step 5d collapse drops the explicit no-recap-between-emit-and-footer ordering (`No free-form recap may appear between or after those pieces`) while only back-referencing a vaguer preamble timing phrase. Scenario: After Step 5c item 5 emits the structured summary, orchestrator inserts free-form recap before Step 5d warning replay or the machine footer, halting mid-Step-5
- **Proposed resolution**: Preserve an explicit Step 5d token forbidding recap between mandatory marker-first emit and warning replay/footer, or strengthen the preamble no-recap rule to name that sub-step boundary ### 1. correctness — `skills/design/SKILL.md` (Approach / preamble stub) The plan binds implementers to preserve only the `/design`-specific deltas enumerated in **Approach** while pointing generic continuation at `subskill-invocation.md#anti-halt`. That list includes step chains, immediate-background boundaries, brainstorm/outline yields, gate re-entries, and intermediate-plan notes, but it never mentions the current preamble’s **visible-output** trigger (`after every visible output (plans, voting tallies, skip breadcrumbs)`). Shared `#anti-halt`’s canonical banner covers numbered-step Bash **helper** calls and child Skill returns, not deliverable-looking visible output. The planned `test-design-structure.sh` additions grep the `#anti-halt` anchor, no-recap/no-cost rules, and the render-exit carve-out, but not visible-output continuation. An implementer following the plan can drop that trigger without failing either harness. **Suggested revision:** Add the visible-output phrase to Approach preserved deltas and the preamble stub, and pin it in `test-design-structure.sh`. ### 2. correctness — `skills/design/SKILL.md` (Step 5d) The plan instructs Step 5d to replace its duplicated binding block with a back-reference to Step 5c item 5 and the preamble no-recap rule. Current Step 5d also forbids recap **between** the mandatory marker-first emit and the warning replay/footer (`No free-form recap may appear between or after those pieces`). The planned preamble shortens recap timing to “after Step 5c or cancellation final-summary render,” which does not encode that intra-Step-5 ordering. **Suggested revision:** Keep an explicit Step 5d ordering token for the emit → warning → footer gap, or strengthen the preamble rule to cover it.



