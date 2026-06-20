## Decision 1: Scope — which items
- **Question**: Issue #4743 bundles 13 independent robustness items. Which should this design plan cover?
- **Resolution**: All 13 items in one plan. Concrete fixes: 1, 3, 4, 5, 8, 9, 12, 13. Investigate-or-close: 2, 6, 7, 10, 11. Do NOT split; #4743 was deliberately combined via `/combine-issues --oos` to cut issue count, so re-splitting is a non-goal.
- **Source**: user

## Decision 2: Disposition for "fix or document/close" items
- **Question**: For items framed as "fix OR document/close" (1, 2, 4, 6, 7, 10, 11), what default disposition should the plan take?
- **Resolution**: Investigate-first. Research each during Step 2b codebase inspection. Land a concrete fix where a real defect exists; otherwise document the no-defect conclusion in the plan and mark that item closed. Matches the issue's own "pin a defect or close as no-defect" framing. Bias toward the smallest change per item.
- **Source**: user

## Hard constraints (carried into plan drafting)
- **Preserve contracts**: run-log append/flush sentinel semantics, `KEY=value` machine stdout grammars, exit-code contracts, and result-env keys consumed by callers must stay byte/behavior stable unless an item explicitly changes them.
- **Independent items**: each of the 13 is independently implementable; the plan must not introduce cross-item coupling that forces all-or-nothing implementation.
- **No-defect items still get a verdict**: investigate-or-close items that find no defect are documented in the plan (not silently dropped) so the implementer closes them deliberately.
