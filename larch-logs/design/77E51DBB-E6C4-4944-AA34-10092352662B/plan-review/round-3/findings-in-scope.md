### FINDING_1: Waterfall regression targets unregistered path
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Edge, Codex-Edge, Cursor-Requirements, Codex-Requirements, Cursor-Pragmatic, Codex-Pragmatic
- **Severity**: important
- **Concern**: The plan points waterfall preservation test work at nonexistent or unregistered `skills/design/scripts/test-revise-plan-with-waterfall.sh` instead of the registered `scripts/test-revise-plan-with-waterfall.sh`, so an implementer could add coverage under the wrong path while `make test-revise-plan-with-waterfall` and `relevant-checks` remain blind to trailer-dropping regressions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch, Codex-Arch, Cursor-Innovation, Codex-Innovation: Change the plan target to scripts/test-revise-plan-with-waterfall.sh and keep its existing sibling contract scripts/test-revise-plan-with-waterfall.md in sync if the documented cases change
  - From Cursor-Edge: Retarget the plan subsection and acceptance bullet to scripts/test-revise-plan-with-waterfall.sh (and scripts/test-revise-plan-with-waterfall.md if documenting cases)
  - From Codex-Edge, Cursor-Requirements, Codex-Requirements: Change the plan target to scripts/test-revise-plan-with-waterfall.sh and scripts/test-revise-plan-with-waterfall.md as needed; do not create an unregistered skill-local harness.
  - From Cursor-Pragmatic, Codex-Pragmatic: Revise the plan target and acceptance text to update scripts/test-revise-plan-with-waterfall.sh and scripts/test-revise-plan-with-waterfall.md, while keeping skills/design/scripts/revise-plan-with-waterfall.sh as the implementation target

### FINDING_2: Advisory-copy validation assigned to wrong harness
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Concern**: The plan assigns combined advisory-copy validation to `test-check-plan-size.sh`, but that harness only executes `check-plan-size.sh` and validates KV output, so it cannot catch incorrect `SKILL.md` Step 2b.5 advisory text such as allowing “proceeding” when `HARD_TRIGGER_FIRED=true`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements, Codex-Requirements: Keep check-plan-size tests KV-focused, and move/add the combined advisory-copy assertion to a small structural check in scripts/test-design-structure.sh that pins SOFT_ADVISORY parsing and the plan-body gate still requires Split/Cancel wording.

### FINDING_3: File-replacement candidates can drop optional trailers
- **Reviewer(s)**: Cursor-dyn-file-replacement-preservation, Codex-dyn-file-replacement-preservation
- **Severity**: important
- **Concern**: Waterfall preservation is only specified in prompt prose; `validate_file_replacement` still accepts candidates with just nonempty content and numeric `diff_lines`, and the emit gate only checks `EMIT_PLAN_STATUS`, so a tier-4 replacement can drop `diff_added`, `diff_deleted`, and `mechanical_churn` while still winning.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-file-replacement-preservation, Codex-dyn-file-replacement-preservation: Add a small mechanical preservation check in revise-plan-with-waterfall.sh for file-replacement candidates: read the original final metadata block, and when original optional trailer keys are present require the replacement candidate to include those strict keys in its final metadata block before accepting it. Keep extract_file_replacement_candidate unchanged because it already captures lines through diff_lines; update the waterfall regression to seed a dropping candidate followed by a preserving candidate and assert the first falls through and the final plan retains the trailers.

### FINDING_4: Boundary test misses blank-separated optional trailer
- **Reviewer(s)**: Cursor-dyn-trailer-scan-boundary, Codex-dyn-trailer-scan-boundary
- **Severity**: important
- **Concern**: The final metadata block boundary test does not cover a full-line optional trailer separated from the true metadata block by a blank line, so an upward scanner that crosses blanks could incorrectly parse or subtract that body line.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-trailer-scan-boundary, Codex-dyn-trailer-scan-boundary: Add one focused check-plan-size case with diff_added above a blank and true metadata below it; assert scan stops at the blank, separated diff_added is body, and PLAN_LINES includes it

### FINDING_5: Duplicate optional-key winner is ambiguous
- **Reviewer(s)**: Cursor-dyn-trailer-scan-boundary, Codex-dyn-trailer-scan-boundary
- **Severity**: important
- **Concern**: The plan does not specify how duplicate optional trailer keys are resolved for an upward scan; “last full-line match wins” could mean last in file order or last encountered while scanning upward, which can choose different values and invert `HARD_TRIGGER_FIRED`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-trailer-scan-boundary, Codex-dyn-trailer-scan-boundary: Specify the intended order explicitly, e.g. last in file order closest to diff_lines wins, and add a duplicate optional-key regression
