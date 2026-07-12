### FINDING_1: Empty sweep handling is undefined
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Concern**: Strict ingestion rejects empty inputs, conflicting with successful zero-commit and zero-finding sweep cases.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Explicitly bypass result-file parsing for zero selected merges and zero refutation queues; still reject empty files when work was dispatched


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


