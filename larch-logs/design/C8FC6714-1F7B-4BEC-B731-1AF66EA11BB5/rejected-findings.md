### [Plan Review] FINDING_9

### FINDING_9: Caller should wait on paired PID file rather than only `$!`
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: Existing fences do not necessarily use shell `&`, and Family B writers already publish `LARCH_PAIRED_PID_FILE`; relying only on `$!` can be stale, unset, or point at the wrong process shape.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Post-monitor wait on PID read from LARCH_PAIRED_PID_FILE (reuse monitor validation); treat $! as optional when & present


### [Plan Review] FINDING_10

### FINDING_10: Monitor-level paired-PID draining may be the more complete fix
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: A fence-only wait fix leaves `breadcrumb-monitor.sh` itself returning on the done sentinel without draining the paired PID, so tool-background and sub-pipeline variants can remain inconsistent across callers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Consider post-done paired-PID drain inside breadcrumb-monitor.sh; keep caller wait as belt-and-suspenders only if needed


### [Plan Review] FINDING_14

### FINDING_14: Backgrounding stdout-capturing writers breaks assignment/eval contracts
- **Reviewer(s)**: Codex-Innovation, Codex-Requirements
- **Severity**: important
- **Concern**: Some Family B-like commands capture stdout through command substitution and eval it later; naively appending `&` backgrounds the assignment in a subshell or loses captured KVs, breaking downstream parsing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Redirect writer stdout to a temp file, monitor, wait, read EXIT_CODE from LARCH_STATUS_FILE, then parse or eval the captured stdout file
  - From Codex-Requirements: Specify a refactor for stdout-capturing writers: redirect writer stdout to a temp file, background the writer, monitor, wait, then read/eval the captured file after completion. Add a lint or harness fixture for this shape


