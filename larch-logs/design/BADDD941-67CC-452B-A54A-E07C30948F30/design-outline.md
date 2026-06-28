## Proposed Design Outline

### Goals
- Remove ~5-7 always-loaded SKILL.md lines by eliminating two verbatim duplicate sentences and one dead `STEP3_REVIEW_LOOP_STATUS`-routing directive
- Fold the residual `SUMMARY_OUTCOME` mapping into the existing `NEXT_ACTION` rows so they are self-contained
- Relocate the `record-escalation` ownership note (and KV-only constraint) from the dropped block into `plan-review.md`

### Non-goals
- No behavior changes; pure prose surgery
- No changes to wrapper scripts, Python code, or test files
- No restructuring of the NEXT_ACTION table or plan-review.md beyond adding one note

### Approach sketch
- Edit `skills/design/SKILL.md`: strip fallback sentence from IMPORTANT block; strip first sentence from auto-error-reporting paragraph; drop the "Step 3 report-gate routing" block; expand the two `NEXT_ACTION=final-summary:*` bullets to include `set SUMMARY_OUTCOME=X` + "run the Final summary block"
- Edit `skills/design/references/plan-review.md`: append the record-escalation ownership note + KV-only constraint as one short note in the "Single-pass review" section, after the existing `design-step3-review.sh` bailout sentence

### Surfaces in scope
- `skills/design/SKILL.md`
- `skills/design/references/plan-review.md`

### Open questions
- None.
