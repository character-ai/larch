### [Plan Review] FINDING_5

### FINDING_5: Pause publish can skip manifest metadata on empty porcelain
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: `design-log-publish.sh` exits early when there are no file changes, so repeat pause publishes can succeed without recording `paused=true` metadata.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: On --reason pause still jq-set manifest.paused even when porcelain empty


### [Plan Review] FINDING_19

### FINDING_19: Resume routing lacks per-step contracts
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The plan says to route directly to `STEP`, but does not define per-step prerequisites, artifacts, or re-derivation rules, leaving implementers to guess how to resume safely.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add a short resume-routing table (or references section) listing per STEP id: prerequisites, artifacts that must exist, and what to re-derive per Decision 5


### [Plan Review] FINDING_23

### FINDING_23: Pause-load should share marker classification/parsing
- **Reviewer(s)**: Cursor-dyn-script-contract-mirror
- **Severity**: important
- **Concern**: Hand-parsing design-pause markers in the loader can diverge from writer classification when whitespace or marker formatting changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-script-contract-mirror: Share classify/extract with named-block-write or add named-block-read.sh


### [Plan Review] FINDING_24

### FINDING_24: Wrapper may change recognizable stderr prefix
- **Reviewer(s)**: Cursor-dyn-script-contract-mirror
- **Severity**: nit
- **Concern**: Delegating through `named-block-write.sh` can change the script-name prefix operators use when grepping failure logs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-script-contract-mirror: Note in plan-block-write.md that errors originate from named-block-write.sh or preserve larch_err prefix in wrapper


