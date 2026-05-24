## Decision 1: Pre-voting plan display scope
- **Question**: Should the plan-display pattern fire only at the two points mentioned in the issue (Step 3 entry + Gate C entry), or also at Step 3.5 Gate B (post-review chooser)?
- **Resolution**: Only the two points in the issue. Do NOT add a re-print at Gate B.
- **Source**: user

## Decision 2: Re-run review panel re-prints
- **Question**: When Gate C selects "Re-run review panel" and Step 3 is re-entered, should the pre-voting plan print fire again?
- **Source**: user
- **Resolution**: No — only on first-time entry to Step 3. Re-entry from Gate C(c) skips the pre-voting plan re-print.

## Decision 3: Step 2b's `## Implementation Plan` print remains unchanged
- **Question**: Does the existing `## Implementation Plan` print at Step 2b stay as-is?
- **Resolution**: Yes — it stays. The new Step 3 entry print is additive and uses a different header to avoid implying it is a different artifact.
- **Source**: codebase (`skills/design/SKILL.md:494` already prints under `## Implementation Plan`)

## Decision 4: Gate C's `## Final Design Plan` print remains the canonical print at the final-approval gate
- **Question**: Does Gate C already print the plan in the current spec?
- **Resolution**: Yes — `skills/design/references/approval-gates.md:115` already mandates "Print the plan under a `## Final Design Plan` header so the user can review it". The plan task confirms this is the canonical Gate C print; verify it actually happens (SKILL.md Step 4b currently says "Execute the Gate C body in approval-gates.md. Present the latest `$DESIGN_TMPDIR/plan.txt`" — verify the wording is unambiguous so executors actually print).
- **Source**: codebase
