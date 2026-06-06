### [Plan Review] FINDING_4

### FINDING_4: Structure harness same-line `--input-file` constraint conflicts with wrapped Step 4 prose
- **Reviewer(s)**: Cursor-dyn-script-contract
- **Severity**: important
- **Concern**: A grep requiring `stall-recovery-issue-input.md` on the same line as `--input-file` conflicts with natural prose wrapping in `stall-recovery.md` Step 4. The harness may fail after a doc rewrite, or authors may contort prose onto one line to satisfy the assertion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-script-contract: Put `/larch:issue --input-file $IMPLEMENT_TMPDIR/stall-recovery-issue-input.md` on one line in step 4, or grep the step-4 section for both tokens without same-line constraint


