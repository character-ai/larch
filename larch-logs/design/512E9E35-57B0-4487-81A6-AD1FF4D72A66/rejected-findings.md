### [Plan Review] FINDING_2

### FINDING_2: Gate C cap lacks executable wiring
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The Gate C re-run cap is only described in prose; without mechanical Step 4b logic, operators can still offer or run review-panel options beyond the intended SIMPLE/HARD caps.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add Step 4b fenced Bash: read review-round-count.txt + design_classification from run-params.json, compute cap, set a shell flag, and branch the Gate C option list before AskUserQuestion (or a tiny gate-c-cap.sh helper)


### [Plan Review] FINDING_9

### FINDING_9: Gate A tier behavior is undefined after trivial removal
- **Reviewer(s)**: Cursor-Arch
- **Severity**: latent
- **Concern**: The new SIMPLE/HARD model does not specify whether Gate A short-circuits or iterates differently by tier, leaving operators with inconsistent discussion depth.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Decide and document: e.g. SIMPLE one-round Gate A short-circuit, HARD may iterate; update approval-gates.md and test-design-structure pins


### [Plan Review] FINDING_17

### FINDING_17: Cap wording conflicts with pre-increment counter semantics
- **Reviewer(s)**: Cursor-Edge, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan describes a re-run cap, but the counter increments before every review entry, making SIMPLE=3 mean three total panel runs rather than three re-runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Rename to max panel runs or increment only on Gate C re-entry


### [Plan Review] FINDING_19

### FINDING_19: Counter increment is prompt-only and can be skipped
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Concern**: Counter updates are specified only in prompt prose, so an orchestrator can skip the increment or cap check and incur unbounded review cost.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Add review-round-counter.sh and call from SKILL Step 3 and Gate C


