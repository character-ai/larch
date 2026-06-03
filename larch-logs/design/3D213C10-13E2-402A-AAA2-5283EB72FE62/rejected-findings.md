### [Plan Review] FINDING_3

### FINDING_3: Plan misstates `build_export` for `write-session-env.sh`
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: nit
- **Concern**: The plan says to use `build_export` in `write-session-env.sh`, but that writer only builds a `KEY=VALUE` `CONTENT` blob (`build_export` exists only in `write-design-current-env.sh`). An implementer may call a nonexistent helper or skip the implement writer change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Use the existing CONTENT+= pattern (same as LARCH_TIMING_LEDGER) for write-session-env; keep build_export only in write-design-current-env.sh


