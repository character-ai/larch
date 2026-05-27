## Decision 1: Scope of "See full plan" option
- **Question**: Should this change be scoped to Gate C only, also include Step 3 entry, or sweep all plan-preview surfaces?
- **Resolution**: All plan-preview surfaces. In practice this means Gate C (Step 4b) AskUserQuestion grows a "See full plan" option, Gate A (Step 1e Shape 2) "Show latest design proposal" is renamed to "See full plan" for label consistency, and the Step 3 entry summary-mode bold-note wording is reviewed for consistency. Gate B manual-mode prompt is unchanged because it is a findings-prompt, not a plan-preview surface (the plan is not currently emitted at Gate B); the issue body explicitly named "approve final plan", not Gate B.
- **Source**: user

## Decision 2: Preserve "Re-run review panel" Gate C option
- **Question**: The user's example listed three options (Approve / See full plan / Discuss more) and omitted "Re-run review panel". Should "Re-run review panel" be preserved when below the tier cap?
- **Resolution**: Keep "Re-run review panel" as a 4th option when below tier cap (SIMPLE=3, HARD=5). At cap, omit it (3 options remain: Approve / See full plan / Discuss further). AskUserQuestion max=4 fits the below-cap shape.
- **Source**: user

## Decision 3: When to offer "See full plan"
- **Question**: Always offer the option regardless of inline-emit mode, or only when summary-mode fires (large plans)?
- **Resolution**: Always offer it. Cleaner option-set: 4 options always below cap, 3 always at cap. No conditional option-presence to document or test.
- **Source**: user

## Decision 4: Rename Gate A Shape 2 label for consistency
- **Question**: Gate A Shape 2 (re-entry from Gate B(c)/Gate C(b)) already has "Show latest design proposal" which is functionally identical to the new Gate C "See full plan". Should it be renamed?
- **Resolution**: Rename Gate A Shape 2 option to "See full plan" for cross-gate label consistency. Gate A's `## Latest Design Plan` header is preserved (it remains informational that the plan may have been revised post-plan).
- **Source**: user

## Decision 5: Behavior after "See full plan" pick (re-fire)
- **Question**: Should "See full plan" remain in the re-fired option list (so users can re-view), or be dropped after the first display?
- **Resolution**: Drop on re-fire. After the user picks "See full plan" at Gate C (or Gate A), `cat` the plan into chat and re-fire the same prompt WITHOUT the "See full plan" option (one fewer option). The remaining options preserve their cap-aware shape (Gate C: Approve / Discuss further / Re-run review panel below cap; Approve / Discuss further at cap. Gate A: Ready for review / Discuss more). User must trigger another full re-display via free-form `Other` if they want it again after re-fire.
- **Source**: user

## Decision 6: Position of "See full plan" in the option list (orchestrator judgment)
- **Question**: Where should "See full plan" sit in the option array?
- **Resolution**: Second position (after Approve, before Discuss further/Re-run). Matches the user's example body ordering (Approve / See full plan / Discuss more). Codebase-inferred.
- **Source**: codebase
