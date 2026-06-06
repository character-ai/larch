### FINDING_1: Header contradicts A2 production launcher changes
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The plan header states the entire batch is test/doc/comment-only with no production behavior change, but A2 edits five production launcher scripts to prepend `DESIGN_TMPDIR`/`LARCH_TIMING_SKILL` pins on `record-vendor-task`. Under polluted `LARCH_TIMING_SKILL=design` shells, vendor rows change skill attribution — contradicting the stated no-behavior-change contract and potentially misleading implementer or PR classification.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Reword the opening constraint to except A2 (surgical launcher pin fix) or drop the blanket no production behavior change line; keep A1/A3/B/C/D as test/doc-only


### FINDING_3: Plan mislabels existing `launch-claude-ci.sh` as NEW
- **Reviewer(s)**: Cursor-dyn-scanner-list-evidence
- **Severity**: nit
- **Concern**: The plan section `### NEW: scripts/launch-claude-ci.sh` contradicts repo state and `staged-context/scope-files.txt`. `scripts/launch-claude-ci.sh` already exists (217-line production CI-fix launcher with unpinned `record-vendor-task` at line 192); `staged-context/scope-files.txt` line 6 lists it as a modify target, not a create.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-scanner-list-evidence: Retitle the plan block to `### UPDATED: scripts/launch-claude-ci.sh (A2 pin only)`; keep the one-line `LARCH_TIMING_SKILL=implement` pin as proposed

