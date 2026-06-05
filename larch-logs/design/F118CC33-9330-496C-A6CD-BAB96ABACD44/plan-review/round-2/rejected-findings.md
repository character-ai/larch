### [Plan Review] FINDING_5

### FINDING_5: Cache JSON schema may break consumers if workflow key is removed
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: latent
- **Concern**: Removing workflow from implement Cache JSON NDJSON changes a durable machine-readable output, even if visible implement tables no longer need workflow columns or grouping.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Keep the workflow key for all skills, using an empty or unknown value for implement, and remove only the markdown workflow grouping/columns


### [Plan Review] FINDING_11

### FINDING_11: timing-ledger.md update may leave subcommands under-documented
- **Reviewer(s)**: Codex-dyn-md-script-pairing
- **Severity**: latent
- **Concern**: The proposed timing-ledger documentation edit only removes workflow behavior, but does not fully restate the remaining subcommands and row types, so the docs can still diverge from the script’s dispatch arms.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-md-script-pairing: When updating timing-ledger.md, make the enum mark/vendor/round and list mark, record-vendor-task, record-round, and dump; remove only workflow-path behavior

