## Proposed Design Outline

### Goals
- Add a third "override and proceed" option to /design's two oversized-feature gate prompts so an operator can knowingly bypass split/cancel.
- The override must prominently warn it is quite likely to severely degrade review quality and the result, and is advised against.
- Record each override as a Warnings audit entry in the run log.

### Non-goals
- Do not change hard-trigger thresholds (plan-body > 800; diff_added > 2000 / diff_lines > 1500) or the mechanical_churn soft-advisory.
- Do not change the --partition flow (its branch fires no AskUserQuestion, so it gains no override).
- Do not add a new flag or a second confirmation gate; the prominent warning is the only guardrail.

### Approach sketch
- Step 2b.5 Hard branch (skills/design/SKILL.md): 2 -> 3 options; override -> proceed to Step 3 plan review with the current oversized plan + Warnings audit entry.
- Step 1c/1d semantic-sprawl prompt (references/discussion-rounds.md): 2 -> 3 options; override -> continue the normal pre-plan flow (no split, no cancel) + Warnings audit entry.
- New option is next-to-last: Split / Override-and-proceed / Cancel. Existing Split + Cancel labels preserved verbatim.
- Update cross-references that assert "no Continue/override" and any structure-test pins on the two-option wording.

### Surfaces in scope
- skills/design/SKILL.md (Step 2b.5 Hard branch + the LOOP_STATUS=plan-size-trigger re-invocation note)
- skills/design/references/discussion-rounds.md (Step 1c + Step 1d sprawl)
- Possibly skills/design/references/approval-gates.md / flags.md (cross-refs only)
- scripts/test-design-structure.sh and any other pins on the current option wording

### Open questions
- None.
