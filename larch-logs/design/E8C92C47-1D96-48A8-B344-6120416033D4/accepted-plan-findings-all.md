### FINDING_3: Auto-dispatching step8-shippr can repeat the unresolved rebase conflict
- **Reviewer(s)**: Cursor-dyn-resume-dispatch-semantics, Codex-dyn-resume-dispatch-semantics
- **Severity**: important
- **Concern**: Mapping `rebase-failed` directly to transient `step8-shippr` dispatch can immediately re-enter Step 8 without `PR_NUMBER`, rerun postbump rebase, and reproduce the same unresolved conflict before the operator can resolve it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-resume-dispatch-semantics: Gate step8-shippr: emit RESUME_HINT=none until a pre-dispatch probe shows origin/main is ancestor of HEAD (or operator clears conflict), then allow step8-shippr; or document that recovery assumes manual rebase first and stall recovery must not auto-dispatch in the same 18a turn
  - From Codex-dyn-resume-dispatch-semantics: Preserve rebase-failed, but do not auto-dispatch it as transient step8-shippr unless the branch is already rebased. Add a dedicated operator-intervention path or non-dispatch classification that tells the operator to manually rebase and resolve conflicts before retrying ship-pr.



