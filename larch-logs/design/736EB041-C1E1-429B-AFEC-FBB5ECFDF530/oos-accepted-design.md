### OOS_1: Step 3 routing still lacks ordered silent-yield handling
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-Prompt Contract Harness
- **Severity**: important
- **Concern**: The Step 3 post-loop routing paragraph in `skills/design/SKILL.md` still tells readers to yield or probe without first ordering empty output, prefix-identical repeats, and first/changed non-empty output. That leaves the repeat-fingerprint silent-yield path easy to miss in the core Step 3 contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add a firm skills/design/SKILL.md bullet to order premature handling: empty output silent yield; prefix-identical repeat (first 200 chars) with absent .completed/step-3-terminal silent yield; first or changed non-empty at most one probe; replace yield or probe wording and add a matching test-design-structure.sh contains pin
  - From Cursor-Innovation: Add a ### UPDATED skills/design/SKILL.md item: before envelope parse, apply empty-output and prefix-identical first-200-chars repeat silent-yield per design-background-wait.md; allow at most one foreground probe only for first or changed non-empty premature output; add a matching contains pin in scripts/test-design-structure.sh
  - From Cursor-Pragmatic: In the `### UPDATED: skills/design/SKILL.md` section, add an explicit Step 3 routing edit: before any probe, apply the prefix-identical first-200-chars silent-yield rule from `design-background-wait.md`; probe only on first or changed non-empty premature output
  - From Cursor-Requirements: Add a ### UPDATED skills/design/SKILL.md bullet ordering premature Step 3 handling: empty output silent yield; prefix-identical repeat (first 200 chars) with absent `.completed/step-3-terminal` silent yield per design-background-wait.md; first or changed non-empty premature output at most one foreground probe; parse only after the terminal sentinel is present.
  - From Cursor-dyn-Prompt Contract Harness: Add a firm ### UPDATED skills/design/SKILL.md bullet for the Step 3 post-loop routing paragraph replace yield or probe with ordered handling empty silent yield prefix-identical repeat first 200 chars with absent step-3-terminal silent yield first or changed non-empty at most one probe sentinel present post-notification sequence


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)
- **Filed URL**: https://github.com/character-ai/larch/issues/6347
### OOS_2: Tier-1 probe prose still mixes repeat-fingerprint carve-out wording
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Requirements, Cursor-dyn-Prompt Contract Harness
- **Severity**: important
- **Concern**: The shared wait rule, AGENTS.md, orchestrator-never, and anti-pattern #4 still use inconsistent repeat wording and fingerprint scope, so a prefix-identical repeat can still look probe-eligible before the silent-yield carve-out.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Require explicit evaluation order in the Step 3 boundary (empty, then prefix-identical repeat, then first/changed non-empty probe) or move the repeat rule above the probe paragraph when replacing byte-identical wording
  - From Cursor-Innovation: Add one sentence to the plan for orchestrator-never.md NEVER #4: prefix-identical first-200-chars repeats with an absent terminal sentinel are not probe-eligible; they follow the NEVER #3 repeat silent-yield carve-out
  - From Cursor-Requirements: Add one Apply carve-out to anti-pattern #4: prefix-identical repeat notifications with an absent fence terminal sentinel are not new recovery turns; end silently per anti-pattern #5 and design-background-wait.md. Update the scripts/test-design-structure.sh foreground-probe contains pin around line 196 so it tolerates the qualified wording.
  - From Cursor-Requirements: Qualify anti-pattern 4 How to apply for new or changed non-empty premature notifications only defer prefix-identical repeats to anti-pattern 5 and design-background-wait.md. Update the line 196 contains pin to the qualified text or add a paired contains pin for the repeat deferral so losing the carve-out fails CI
  - From Cursor-dyn-Prompt Contract Harness: Add universal-rule repeat carve-out prefix-identical first 200 chars same wait absent fence terminal sentinel silent yield no tool ScheduleWakeup or prose or state Step 5c and Final summary extra_guards Parameters carry the repeat rule so universal prose stays aligned
  - From Cursor-dyn-Prompt Contract Harness: Add when the relevant terminal sentinel is absent and the first 200 chars match the prior non-empty notification in the same wait to the AGENTS.md carve-out matching other surfaces
  - From Cursor-dyn-Prompt Contract Harness: Anti-pattern 4 still mandates one foreground terminal-sentinel probe per recovery turn for any premature non-empty notification harness line 196 contains-pins that literal so CI keeps enforcing probe-first guidance even if repeat carve-outs land elsewhere Qualify anti-pattern 4 How to apply for new or changed non-empty premature notifications only defer prefix-identical repeats to anti-pattern 5 and design-background-wait.md update the line 196 contains pin to the qualified text or add a paired contains pin for the repeat deferral so losing the carve-out fails CI


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### OOS_3: Generic Immediate-background wait rule still orders probe-before-repeat for non-empty premature output
- **Description**: Generic Immediate-background wait rule still orders probe-before-repeat for non-empty premature output. Scenario: Step 3 loads both the generic rule and the Step 3 boundary; precedence is implicit only, so a reader applying the generic paragraph first may still probe on repeats
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/shared/design-background-wait.md:15
- **Phase**: design




Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral

### OOS_4: Step 5c repeat contract is local prose only while Final summary and Step 4 waits still lack explicit repeat routing
- **Description**: Step 5c repeat contract is local prose only while Final summary and Step 4 waits still lack explicit repeat routing. Scenario: Those waits also use immediate-background mode and can emit duplicate non-empty notifications, but the issue scope centers on Step 3 and Step 5c; extending repeat routing to every wait is extra surface not required to close #6309 OOS items
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:622-622
- **Phase**: design




Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral

### OOS_5: Generic Immediate-background wait rule still lacks a repeat carve-out
- **Description**: Generic Immediate-background wait rule still lacks a repeat carve-out. Scenario: Step 5c reads the generic rule before its local Parameters; only the Step 3 boundary section and SKILL Step 5c prose are planned. Step 4 and Final summary waits that share the generic rule would still read probe-on-non-empty only.
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/shared/design-background-wait.md:15
- **Phase**: design




Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral

### OOS_6: AGENTS.md Tier-1 literals are also pinned in the anti-polling harness
- **Description**: AGENTS.md Tier-1 literals are also pinned in the anti-polling harness. Scenario: The plan updates AGENTS.md and test-design-structure.sh only. AGENTS repeat prose could drift while test-implement-anti-polling-rule.sh still passes on stale literals.
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: scripts/test-implement-anti-polling-rule.sh
- **Phase**: design




Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral

### OOS_7: Probe paragraph still precedes the repeat-fingerprint paragraph
- **Description**: Probe paragraph still precedes the repeat-fingerprint paragraph. Scenario: Even with prefix-identical wording fixed, line 29 authorizes probing on any non-empty premature output before line 33 states the repeat exception. Close readers may probe before checking the fingerprint.
- **Reviewer**: Cursor-Requirements
- **Severity**: nit
- **Focus area**: correctness
- **Location**: skills/shared/design-background-wait.md:29-33
- **Phase**: design

Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_8: Step 3 routing still probe-first on repeats
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: The firm `skills/design/SKILL.md` update list never requires rewriting the Step 3 post-loop `NEXT_ACTION` preamble, so the live routing text can still treat premature notifications as “yield or probe” without first silent-yielding prefix-identical repeats. That leaves the Step 3 control path able to foreground-probe repeat notifications even after the surrounding anti-pattern and wait prose change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add a firm `skills/design/SKILL.md` bullet to amend the Step 3 post-loop routing preamble (~413) with the same ordered contract as the updated anti-pattern: empty output → silent yield; prefix-identical repeat over the first 200 chars with absent `{terminal_sentinel}` → silent yield; first/changed non-empty premature output → at most one foreground probe.
  - From Cursor-Innovation: Add a firm bullet under ### UPDATED: skills/design/SKILL.md to rewrite the Step 3 post-loop premature-notification paragraph before the NEXT_ACTION table: empty output silent yield; prefix-identical repeat over the first 200 chars with the active terminal sentinel absent silent yield; first or changed non-empty premature output at most one foreground probe per shared rules; only then parse when the terminal sentinel is present.
  - From Cursor-Pragmatic: Add a firm ### UPDATED: skills/design/SKILL.md bullet to rewrite the post-loop premature-notification preamble with the ordered contract: empty output silent yield; prefix-identical repeat over the first 200 chars with absent active terminal sentinel silent yield; first or changed non-empty premature notification at most one foreground probe; sentinel present then post-notification routing.
  - From Cursor-Requirements: In `skills/design/SKILL.md` Step 3 post-loop routing, replace yield or probe without parsing with an explicit ordered rule: empty output ends silently; prefix-identical repeat (first 200 chars) with absent `{terminal_sentinel}` ends silently; first or changed non-empty premature output gets at most one foreground probe; proceed only after the terminal sentinel is present.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### OOS_9: [OUT_OF_SCOPE] Generic Immediate-background wait rule still probes on any non-empty premature notification without a repeat carve-out
- **Description**: [OUT_OF_SCOPE] Generic Immediate-background wait rule still probes on any non-empty premature notification without a repeat carve-out. Scenario: The plan updates the Step 3 fingerprint paragraph and Tier-1 surfaces but leaves the shared Immediate-background wait rule at line 15 unchanged. Final summary and Step 4 tail fences load that generic rule first and can still treat prefix-identical repeats as probe-eligible before operators reach the Step 3-only repeat paragraph.
- **Reviewer**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/shared/design-background-wait.md:15
- **Phase**: design




Vote tally: YES=0 NO=2 JUDGE_ERROR=1 Result=rejected

### OOS_10: [OUT_OF_SCOPE] Generic Immediate-background wait rule still lacks a repeat carve-out
- **Description**: [OUT_OF_SCOPE] Generic Immediate-background wait rule still lacks a repeat carve-out. Scenario: The plan limits repeat-fingerprint wording to the Step 3 subsection, orchestrator-never, AGENTS.md, anti-pattern #5, and explicit Step 5c prose. The shared generic rule at line 15 still says any non-empty premature notification may take one foreground probe with no prefix-identical repeat exception, so Final summary and Step 4 callers that load only that section can still probe on repeated identical output.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/shared/design-background-wait.md:15
- **Phase**: design




Vote tally: YES=0 NO=2 JUDGE_ERROR=1 Result=rejected

### OOS_11: Generic Immediate-background wait rule still lacks a repeat carve-out
- **Description**: Generic Immediate-background wait rule still lacks a repeat carve-out. Scenario: The plan updates only the Step 3 fingerprint paragraph and adds local Step 5c repeat prose. The shared Immediate-background wait rule at line 15 still authorizes a foreground probe on any non-empty premature notification with no prefix-identical repeat exception, so Step 4 and Final summary waits can still probe on repeats.
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/shared/design-background-wait.md:15
- **Phase**: design

Vote tally: YES=0 NO=2 JUDGE_ERROR=1 Result=rejected
