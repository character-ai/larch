### FINDING_1:
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-revise-plan-with-waterfall.sh:1
- **Concern**: The plan targets nonexistent skills/design/scripts/test-revise-plan-with-waterfall.sh for the waterfall preservation regression. Scenario: The implementer may add or update an unregistered sibling path, leaving the Makefile/relevant-checks harness without the required optional-trailer preservation coverage
- **Proposed resolution**: Change the plan target to scripts/test-revise-plan-with-waterfall.sh and keep its existing sibling contract scripts/test-revise-plan-with-waterfall.md in sync if the documented cases change

### FINDING_2:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:93-97
- **Concern**: Waterfall preservation harness path points at skills/design/scripts/ but the registered harness lives under scripts/. Scenario: Implementer may add or edit the wrong file; Makefile still runs scripts/test-revise-plan-with-waterfall.sh so the new regression never runs
- **Proposed resolution**: Retarget the plan subsection and acceptance bullet to scripts/test-revise-plan-with-waterfall.sh (and scripts/test-revise-plan-with-waterfall.md if documenting cases)

### FINDING_3:
- **Reviewer(s)**: Codex-Edge, Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: Makefile:968-969
- **Concern**: Plan updates a non-existent waterfall preservation harness path. Scenario: The plan names skills/design/scripts/test-revise-plan-with-waterfall.sh, but the registered harness is scripts/test-revise-plan-with-waterfall.sh. An implementer could add the regression under the wrong path, leaving make test-revise-plan-with-waterfall and relevant-checks blind to optional trailer loss.
- **Proposed resolution**: Change the plan target to scripts/test-revise-plan-with-waterfall.sh and scripts/test-revise-plan-with-waterfall.md as needed; do not create an unregistered skill-local harness.

### FINDING_4:
- **Reviewer(s)**: Cursor-Pragmatic, Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:93, scripts/test-revise-plan-with-waterfall.sh:1-7, Makefile:968-969
- **Concern**: Plan names a nonexistent waterfall test path. Scenario: The registered Makefile target runs scripts/test-revise-plan-with-waterfall.sh, so adding the preservation regression under skills/design/scripts/test-revise-plan-with-waterfall.sh would leave the real harness unchanged and fail to catch trailer-dropping revisions
- **Proposed resolution**: Revise the plan target and acceptance text to update scripts/test-revise-plan-with-waterfall.sh and scripts/test-revise-plan-with-waterfall.md, while keeping skills/design/scripts/revise-plan-with-waterfall.sh as the implementation target

### FINDING_5:
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:82-88,142-144; skills/design/scripts/test-check-plan-size.sh:43-49; scripts/test-design-structure.sh:342-354
- **Concern**: Combined advisory-copy validation is assigned to the wrong harness. Scenario: test-check-plan-size.sh only executes check-plan-size.sh and validates KV output, so it cannot catch SKILL.md Step 2b.5 printing the wrong advisory text, such as using proceeding when HARD_TRIGGER_FIRED=true. That leaves the stated SKILL.md advisory-copy acceptance unvalidated.
- **Proposed resolution**: Keep check-plan-size tests KV-focused, and move/add the combined advisory-copy assertion to a small structural check in scripts/test-design-structure.sh that pins SOFT_ADVISORY parsing and the plan-body gate still requires Split/Cancel wording.

### FINDING_6:
- **Reviewer(s)**: Cursor-dyn-file-replacement-preservation, Codex-dyn-file-replacement-preservation
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:70-73; skills/design/scripts/revise-plan-with-waterfall.sh:481-494,514-520
- **Concern**: Waterfall preservation is specified as prompt prose, but file-replacement validation still accepts any nonempty candidate whose last nonblank line is numeric diff_lines, and the emit gate only checks EMIT_PLAN_STATUS.. Scenario: The first tier-4 file-replacement candidate can drop diff_added, diff_deleted, and mechanical_churn, pass validate_file_replacement and run_emit_plan_gate, and become the winner; later size checks see only legacy diff_lines, so the mechanical/deletion exemption is silently lost.
- **Proposed resolution**: Add a small mechanical preservation check in revise-plan-with-waterfall.sh for file-replacement candidates: read the original final metadata block, and when original optional trailer keys are present require the replacement candidate to include those strict keys in its final metadata block before accepting it. Keep extract_file_replacement_candidate unchanged because it already captures lines through diff_lines; update the waterfall regression to seed a dropping candidate followed by a preserving candidate and assert the first falls through and the final plan retains the trailers.

### FINDING_7:
- **Reviewer(s)**: Cursor-dyn-trailer-scan-boundary, Codex-dyn-trailer-scan-boundary
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:21-28,75-88
- **Concern**: Final metadata block boundary test omits a blank-separated full-line optional trailer. Scenario: A valid-looking diff_added line above a blank separator can be incorrectly parsed or subtracted if the upward scan crosses blanks; the proposed spoof test does not explicitly assert PLAN_LINES includes that separated line
- **Proposed resolution**: Add one focused check-plan-size case with diff_added above a blank and true metadata below it; assert scan stops at the blank, separated diff_added is body, and PLAN_LINES includes it

### FINDING_8:
- **Reviewer(s)**: Cursor-dyn-trailer-scan-boundary, Codex-dyn-trailer-scan-boundary
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:21-24,107-116; skills/design/scripts/test-check-plan-size.sh:178-192
- **Concern**: Duplicate optional key winner is ambiguous for an upward scan. Scenario: Last full-line match wins can mean last in file order or last encountered while scanning upward; those choose different diff_added values and can invert HARD_TRIGGER_FIRED
- **Proposed resolution**: Specify the intended order explicitly, e.g. last in file order closest to diff_lines wins, and add a duplicate optional-key regression
