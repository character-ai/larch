## Proposed Design Outline

### Goals
- Add a structured "See full plan" option to Gate C (Step 4b) `AskUserQuestion` so users don't need `Other` + free-form text to view the plan.
- Rename Gate A Shape 2 (post-plan re-entry) option from "Show latest design proposal" to "See full plan" for cross-gate label consistency.
- Drop "See full plan" from the re-fired prompt after one display (so the prompt shrinks naturally after the plan has just been shown).

### Non-goals
- No changes to Gate B (manual or auto-apply) — Gate B is finding-focused, not a plan-preview surface.
- No changes to Step 3 plan-candidate emit (no AskUserQuestion exists at Step 3; the existing inline emit + free-form interrupt is unchanged).
- No changes to `LARCH_DESIGN_PLAN_SUMMARY_THRESHOLD`, the summary-mode threshold (>120 default), the section-outline format, or the empty-outline fallback in `emit-design-plan-preview.sh`.

### Approach sketch
- **Gate C**: 2nd-position "See full plan" option. Below cap = 4 options (Approve final design / See full plan / Discuss further / Re-run review panel). At cap = 3 options (Approve / See full plan / Discuss further). Re-fire after "See full plan" omits the option (3 / 2 respectively).
- **Gate A Shape 2**: 1st-position option renamed to "See full plan" (replaces "Show latest design proposal"). Header `## Latest Design Plan` preserved. Re-fire after "See full plan" omits it (2 options: Ready for review / Discuss more).
- **`emit-design-plan-preview.sh`**: Update `_large_note_gatec` bold-note wording to reference the structured option instead of "pick Other". Step 3 large-note unchanged because Step 3 has no `AskUserQuestion`.
- **Tests**: Update `skills/design/scripts/test-emit-design-plan-preview.sh` to assert the new Gate C bold-note wording; sweep `scripts/test-design-structure.sh` and other tests for any literal "Show latest design proposal" / Gate C option pins and adjust.

### Surfaces in scope
- `skills/design/SKILL.md` (Step 4b Gate C prose; Step 1e Gate A pointer)
- `skills/design/references/approval-gates.md` (Gate A Shape 2; Gate C)
- `skills/design/scripts/emit-design-plan-preview.sh` (Gate C bold-note only)
- `skills/design/scripts/test-emit-design-plan-preview.sh` (assertions on new bold-note)
- `scripts/test-design-structure.sh` and any other tests that pin Gate A/C option labels

### Open questions
- None.
