### [Plan Review] FINDING_5

### FINDING_5: Design MAV snapshot deletes persisted round start time
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The design MAV branch persists `round-start-s` inside the round directory, but `_snapshot_round_dir` deletes round-dir files before repopulating allowed artifacts, so deferred timing can lose its start timestamp.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Exempt `round-start-s` from the `dest/*` deletion loop (or copy it into `tmp` before wipe), or persist start time outside `plan-review/round-N/` (e.g. `$DESIGN_TMPDIR/plan-review-round-$N-start-s`)


### [Plan Review] FINDING_6

### FINDING_6: Design OOS timing data exceeds stated feature scope
- **Reviewer(s)**: Codex-Requirements
- **Severity**: latent
- **Concern**: The plan adds design-only round `oos` data, expanding the timing-report JSON shape and parser/tests beyond the stated minimum-change acceptance contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Drop `--oos`, the design OOS counting/parser, and related tests/docs unless the feature description is updated to require OOS counts


### [Plan Review] FINDING_8

### FINDING_8: Deferred timing helpers can duplicate round rows on retry
- **Reviewer(s)**: Codex-dyn-deferred-handoff
- **Severity**: latent
- **Concern**: Deferred round helpers are not specified as idempotent, so retries or resumes can record duplicate timing rows for the same round.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-deferred-handoff: Add duplicate suppression in the new deferred helpers, e.g. skip when the bound ledger already has the same skill/step/round/start tuple, and cover retry with a focused test


