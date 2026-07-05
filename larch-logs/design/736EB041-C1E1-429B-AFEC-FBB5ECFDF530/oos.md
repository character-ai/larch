### FINDING_1: Step 3 routing still probe-first on repeats
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: The firm `skills/design/SKILL.md` update list never requires rewriting the Step 3 post-loop `NEXT_ACTION` preamble, so the live routing text can still treat premature notifications as “yield or probe” without first silent-yielding prefix-identical repeats. That leaves the Step 3 control path able to foreground-probe repeat notifications even after the surrounding anti-pattern and wait prose change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add a firm `skills/design/SKILL.md` bullet to amend the Step 3 post-loop routing preamble (~413) with the same ordered contract as the updated anti-pattern: empty output → silent yield; prefix-identical repeat over the first 200 chars with absent `{terminal_sentinel}` → silent yield; first/changed non-empty premature output → at most one foreground probe.
  - From Cursor-Innovation: Add a firm bullet under ### UPDATED: skills/design/SKILL.md to rewrite the Step 3 post-loop premature-notification paragraph before the NEXT_ACTION table: empty output silent yield; prefix-identical repeat over the first 200 chars with the active terminal sentinel absent silent yield; first or changed non-empty premature output at most one foreground probe per shared rules; only then parse when the terminal sentinel is present.
  - From Cursor-Pragmatic: Add a firm ### UPDATED: skills/design/SKILL.md bullet to rewrite the post-loop premature-notification preamble with the ordered contract: empty output silent yield; prefix-identical repeat over the first 200 chars with absent active terminal sentinel silent yield; first or changed non-empty premature notification at most one foreground probe; sentinel present then post-notification routing.
  - From Cursor-Requirements: In `skills/design/SKILL.md` Step 3 post-loop routing, replace yield or probe without parsing with an explicit ordered rule: empty output ends silently; prefix-identical repeat (first 200 chars) with absent `{terminal_sentinel}` ends silently; first or changed non-empty premature output gets at most one foreground probe; proceed only after the terminal sentinel is present.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### OOS_1: [OUT_OF_SCOPE] Generic Immediate-background wait rule still probes on any non-empty premature notification without a repeat carve-out
- **Description**: [OUT_OF_SCOPE] Generic Immediate-background wait rule still probes on any non-empty premature notification without a repeat carve-out. Scenario: The plan updates the Step 3 fingerprint paragraph and Tier-1 surfaces but leaves the shared Immediate-background wait rule at line 15 unchanged. Final summary and Step 4 tail fences load that generic rule first and can still treat prefix-identical repeats as probe-eligible before operators reach the Step 3-only repeat paragraph.
- **Reviewer**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/shared/design-background-wait.md:15
- **Phase**: design




Vote tally: YES=0 NO=2 JUDGE_ERROR=1 Result=rejected

### OOS_2: [OUT_OF_SCOPE] Generic Immediate-background wait rule still lacks a repeat carve-out
- **Description**: [OUT_OF_SCOPE] Generic Immediate-background wait rule still lacks a repeat carve-out. Scenario: The plan limits repeat-fingerprint wording to the Step 3 subsection, orchestrator-never, AGENTS.md, anti-pattern #5, and explicit Step 5c prose. The shared generic rule at line 15 still says any non-empty premature notification may take one foreground probe with no prefix-identical repeat exception, so Final summary and Step 4 callers that load only that section can still probe on repeated identical output.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/shared/design-background-wait.md:15
- **Phase**: design




Vote tally: YES=0 NO=2 JUDGE_ERROR=1 Result=rejected

### OOS_3: Generic Immediate-background wait rule still lacks a repeat carve-out
- **Description**: Generic Immediate-background wait rule still lacks a repeat carve-out. Scenario: The plan updates only the Step 3 fingerprint paragraph and adds local Step 5c repeat prose. The shared Immediate-background wait rule at line 15 still authorizes a foreground probe on any non-empty premature notification with no prefix-identical repeat exception, so Step 4 and Final summary waits can still probe on repeats.
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/shared/design-background-wait.md:15
- **Phase**: design

Vote tally: YES=0 NO=2 JUDGE_ERROR=1 Result=rejected

