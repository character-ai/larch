### FINDING_1:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:5-8
- **Concern**: Header claims entire batch is test/doc/comment-only with no production behavior change. Scenario: A2 edits five production launcher scripts to prepend DESIGN_TMPDIR/LARCH_TIMING_SKILL pins on record-vendor-task; under polluted LARCH_TIMING_SKILL=design shells vendor rows change skill attribution — contradicts the stated no-behavior-change contract and can mislead implementer/PR classification
- **Proposed resolution**: Reword the opening constraint to except A2 (surgical launcher pin fix) or drop the blanket no production behavior change line; keep A1/A3/B/C/D as test/doc-only

### FINDING_2:
- **Reviewer(s)**: Cursor-dyn-commit-sequence
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:10-83
- **Concern**: Files to modify lists A1 harness before A2 launcher pins while Approach requires A2 first. Scenario: The section opens with scripts/test-implement-structure.sh (A1+A3) then lists five A2 launcher files. An implementer editing or committing top-to-bottom—or splitting item A into an A1-then-A2 commit—lands the scanner while record-vendor-task lines at scripts/launch-codex-implement.sh:230 scripts/launch-cursor-implement.sh:169 scripts/launch-codex-ci.sh:247 scripts/launch-cursor-ci.sh:230 and scripts/launch-claude-ci.sh:192 remain unpinned, so the new A1 guard fails until every A2 pin is present
- **Proposed resolution**: Reorder Files to modify so all A2 launcher entries precede scripts/test-implement-structure.sh, or add an explicit Commit sequence bullet stating file-list order is not commit order and A2 pins must be committed with or before A1

### FINDING_3:
- **Reviewer(s)**: Cursor-dyn-scanner-list-evidence
- **Severity**: nit
- **Focus area**: correctness
- **Location**: scripts/launch-claude-ci.sh:1-6
- **Concern**: Plan section `### NEW: scripts/launch-claude-ci.sh` contradicts repo state and scope-files.txt. Scenario: `scripts/launch-claude-ci.sh` already exists (217-line production CI-fix launcher with unpinned `record-vendor-task` at line 192); `staged-context/scope-files.txt` line 6 lists it as a modify target, not a create
- **Proposed resolution**: Retitle the plan block to `### UPDATED: scripts/launch-claude-ci.sh (A2 pin only)`; keep the one-line `LARCH_TIMING_SKILL=implement` pin as proposed
