### [Plan Review] FINDING_10

### FINDING_10: Step 2b fat guards preempt rc10/11/12/13 dispatch
- **Reviewer(s)**: Cursor-dyn-exit-code-mapper
- **Severity**: important
- **Concern**: Existing post-driver mandatory-key, `VALIDATE_STATUS`, and generic nonzero guards can run before the intended thin `case` dispatch, preventing rc10/11/12/13 from reaching their handlers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-exit-code-mapper: Replace the Step 2b fence with echo-then-case only: drop stdout KV merge and the rc 0/1 mandatory-key gate for merged `--with-plan-size` calls; route defects via rc 10 (not `VALIDATE_STATUS` after rc 0); handle 11/12/13 before the generic `ne 0` abort


