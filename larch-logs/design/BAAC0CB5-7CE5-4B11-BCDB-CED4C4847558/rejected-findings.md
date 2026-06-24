### [Plan Review] FINDING_5

### FINDING_5: Step 4b still mandates duplicate Gate C mechanical preview
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The primary `SKILL.md` update retargets mechanical emit to `design-step3b-tail.sh`, but Step 4b prose still requires `design-step4b-preview.sh` and, on `--skip-approve`, to "still run the Gate C preview" at 4b. Step 4 tail already runs `plan-review preview --variant gatec` today. Leaving 4b prose yields duplicate `## Final Design Plan` emits and violates the cost/context-bloat constraint.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: In the SKILL.md update, delete the Step 4b "Mechanical Gate C plan emit" paragraph and the `--skip-approve` "still run preview" instruction; Gate C Presentation should consume tail stdout only on the normal path (resume file-read stays narrow per plan).
  - From Cursor-Pragmatic: In the `skills/design/SKILL.md` Step 4b delta, delete/replace lines 755-759: Gate C mechanical preview and `SKIP_APPROVE_REQUESTED_GATEC` parsing come only from Step 4 tail stdout; Step 4b loads `dialectic-clarifier.md` per deferred-load guard and runs `approval-gates.md` Presentation/Prompt only, with no second `plan-review preview --variant gatec`.


