### OOS_1: Issue scope names skill-editing-trace coordination; the plan does not widen `paths:` for new `skills/*/references/*.md` normative files.
- **Description**: Issue scope names skill-editing-trace coordination; the plan does not widen `paths:` for new `skills/*/references/*.md` normative files.. Scenario: `finalize-step5.md` and `step18-cleanup.md` edits will not trigger the trace reminder, weakening helper/test tracing called out in the issue risk section.
- **Reviewer**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: .claude/rules/skill-editing-trace.md:2
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_2: Plan relocates Step 18 orchestrator prose to `step18-cleanup.md` but does not list sibling wrapper contract `step-18.md`.
- **Description**: Plan relocates Step 18 orchestrator prose to `step18-cleanup.md` but does not list sibling wrapper contract `step-18.md`.. Scenario: `step-18.md` still describes Step 18a.5 placement and stall handoff inline; after the move it can drift from SKILL/reference authority without any harness pin.
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/implement/scripts/step-18.md:20-23
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_3: `require_near` only checks co-occurrence within a char window, not that the read line precedes the fence.
- **Description**: `require_near` only checks co-occurrence within a char window, not that the read line precedes the fence.. Scenario: A read placed after `ship route-exit` or `step-18.sh --phase gate` but within ±1200 chars of the anchor can still satisfy the check, skipping relocated authority on first entry.
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: scripts/test-implement-structure.sh:23-31
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_4: Issue scope names skill-editing-trace coordination; plan still does not widen `paths:` for new `skills/*/references/*.md` normative files
- **Description**: Issue scope names skill-editing-trace coordination; plan still does not widen `paths:` for new `skills/*/references/*.md` normative files. Scenario: The glob covers `skills/**/SKILL.md`, scripts, and `skills/shared/*.md` but not `skills/design/references/finalize-step5.md` or `skills/implement/references/step18-cleanup.md`. Edits to those references will not trigger the trace reminder, weakening helper/test tracing the issue calls out.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: .claude/rules/skill-editing-trace.md:2
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_5: Issue binding scope requires landing after #5273 and #5276; plan has no merge/land ordering note
- **Description**: Issue binding scope requires landing after #5273 and #5276; plan has no merge/land ordering note. Scenario: Both upstream issues touch the same SKILL.md regions this relocation targets. Implementing first can relocate prose those PRs delete or rewrite, then reintroduce conflicts and duplicate authority on retry.
- **Reviewer**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_6: Issue scope names skill-editing-trace coordination, but the plan does not widen the rule `paths:` glob for new `skills/*/references/*.md` normative files.
- **Description**: Issue scope names skill-editing-trace coordination, but the plan does not widen the rule `paths:` glob for new `skills/*/references/*.md` normative files.. Scenario: `finalize-step5.md` and `step18-cleanup.md` will not trigger the trace reminder when edited alone, weakening helper/test tracing called out in scope.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: architecture
- **Location**: .claude/rules/skill-editing-trace.md:2
- **Phase**: design

Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

