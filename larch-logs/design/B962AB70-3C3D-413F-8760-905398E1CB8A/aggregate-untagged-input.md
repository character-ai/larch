### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/design_lifecycle.py:step5c_core
- **Concern**: Pause handling must return before publish work. Scenario: Plan says invoke design pause-save before publish but not return early; publish_core can still run while pause is active
- **Proposed resolution**: Bind pause like step5b_prepare_main: if .pause-requested exists return _call_pause_save(design_tmpdir) (or check_pause_and_exit) before bg marker and publish_core; do not fall through

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-step5c.sh:209-211
- **Concern**: Step 5c omits the rc=3 operator warning line. Scenario: SKILL.md Step 5c item 839 tells the orchestrator to continue after publish rc=3 with the WARN above; the current Bash wrapper prints **⚠ Step 5c: design-publish.sh result-env write failed (exit 3); continuing with stdout parse** to stderr before stdout fallback parsing. The plan never requires an equivalent _core_diagnostic or contract-stream line after adding publish_core rc=3.
- **Proposed resolution**: After the in-process port, rc=3 runs may continue mechanically but without the driver-visible warning the orchestrator contract expects.

### FINDING_3:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/design_lifecycle.py:step5c_core
- **Concern**: In-process publish_core must capture all stdout, not only KV rows. Scenario: The plan says capture publish stdout to a temp file but does not require isolating the in-process call. publish_core prints KV rows plus refusal and security warnings. Without redirect_stdout (or _capture_stdout) those lines land on the Step 5c contract stream and can duplicate or precede allowlisted rows the orchestrator parses.
- **Proposed resolution**: Wrap publish_core in full stdout capture to the temp file (same pattern as step_final_summary_core render capture). Emit only allowlisted rows and disk-based markers on the contract stream afterward.

### FINDING_4:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/design_lifecycle.py:step5c_core
- **Concern**: In-process publish capture unspecified under quiet_init. Scenario: After step5c_main calls quiet_init, publish_core print() routes to the quiet log, not a subprocess-captured stdout file. A naive temp-file capture will miss PLAN_WRITE_OK and other rows needed for rc 1/3/4 stdout-authority parsing.
- **Proposed resolution**: Wrap publish_core with the same capture pattern used elsewhere in design_lifecycle (contextlib.redirect_stdout to a temp capture file, or _capture_contract_stream_to_paths). Parse that capture for read-result-env fallback. Emit step5c contract rows separately via emit_kv.

### FINDING_5:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:65-74
- **Concern**: The proposed Step 5c stdout row list omits existing contract rows: PUBLISH_RC, PLAN_WRITE_OK, PUBLISH_OK, and CLEANUP_ELIGIBLE. Scenario: After the background Step 5c task completes, the orchestrator cannot reliably branch on publish rc, plan-write failure, success footer, or cleanup eligibility from the task output, regressing the current wrapper contract
- **Proposed resolution**: Add those four rows to the required emitted stdout rows and assert them in the Step 5c lifecycle tests.
