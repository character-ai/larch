### FINDING_1: Empty sweep handling is undefined
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Concern**: Strict ingestion rejects empty inputs, conflicting with successful zero-commit and zero-finding sweep cases.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Explicitly bypass result-file parsing for zero selected merges and zero refutation queues; still reject empty files when work was dispatched

### FINDING_2: Pinned tip may diverge from the checked-out tip
- **Reviewer(s)**: Codex-Arch
- **Severity**: minor
- **Concern**: Refetching `origin/main` after preflight can cause agents to inspect a checkout that differs from the pinned sweep SHA.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Capture and pass the preflight SHA through the workflow, or verify main and origin/main equal the pinned SHA before dispatch and fail closed

### FINDING_3: First-parent enumeration is not explicit
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Concern**: Without an explicit `--first-parent` Git invocation, enumeration may include side-branch commits that were not on main’s first-parent line.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Specify enumeration as git log --first-parent <watermark>..<pinned-tip> (or equivalent rev-list), keep the same exclusion filters, and add a fixture that would include a side-branch-only commit without --first-parent.

### FINDING_4: Sweep ingestion lacks executable fail-closed fences
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Concern**: The workflow does not require executable Python ingestion steps or exact acceptance enforcement, allowing prompt-side validation and partial success.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Mirror triage/deep: add bash fences for sweep prepare, ingest-finder, and ingest-refuter; save finder JSONL under fixed RUN_DIR paths; abort the run on any non-zero ingest exit before refuter dispatch or legacy stages.

### FINDING_5: Refuter dispatch handoff is unspecified
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Concern**: The refuter queue path, required output keys, per-task inputs, and exact coverage validation are not defined.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Have ingest-finder emit REFUTER_QUEUE_PATH plus queue length KVs; document that S2 dispatches one refuter per queue row using only that file; require ingest-refuter to verify the accepted key set exactly matches the queue before writing the validated sweep-result artifact.
