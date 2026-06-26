## Proposed Design Outline

### Goals
- Add explicit inline prohibition to `/design` SKILL.md against omitting `### Round N reviewer timing` Gantt sections when emitting the final summary verbatim
- Achieve parity with `/implement` SKILL.md fix (#5376) which already has this prohibition

### Non-goals
- No changes to Python code (`design_summary.py`, `review_phase_detail.py`, `progress_report.py`) — code is correct, tests pass
- No changes to `skills/shared/final-summary-emit.md` — it already has the required language
- No changes to Gantt chart generation logic

### Approach sketch
- Locate the anti-halt continuation reminder (line 29 of `skills/design/SKILL.md`) and add "Verbatim means the entire marker body..." prohibition after the "marker-first profile." phrase
- Locate Step 5c item 5 (line 842) and add the same prohibition after the profile reference
- Locate Step 5d (line 852) and add the prohibition after "No free-form recap may appear between or after those pieces."

### Surfaces in scope
- `skills/design/SKILL.md` — three inline text additions to existing paragraphs

### Open questions
- None.
