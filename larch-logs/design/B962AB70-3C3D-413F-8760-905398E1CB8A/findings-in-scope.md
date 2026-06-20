### FINDING_1: Pause must return before publish work
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The plan says to invoke `design pause-save` when `.pause-requested` exists before publish work, but does not require an early return. Without binding pause like `step5b_prepare_main`, `publish_core` can still run while pause is active.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Bind pause like step5b_prepare_main: if .pause-requested exists return _call_pause_save(design_tmpdir) (or check_pause_and_exit) before bg marker and publish_core; do not fall through

### FINDING_2: rc=3 operator warning missing from in-process port
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The current Bash wrapper prints a driver-visible stderr warning when publish returns rc=3 before stdout fallback parsing. The plan does not require an equivalent `_core_diagnostic` or contract-stream warning after the in-process port, so rc=3 runs may continue mechanically without the orchestrator-visible warning `SKILL.md` expects.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: After the in-process port, rc=3 runs may continue mechanically but without the driver-visible warning the orchestrator contract expects.

### FINDING_3: In-process publish stdout capture must work under quiet_init
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: The plan says to capture publish stdout to a temp file but does not specify isolation of the in-process `publish_core` call. `publish_core` prints KV rows plus refusal and security warnings. Without full stdout capture, those lines can land on the Step 5c contract stream and duplicate or precede allowlisted rows the orchestrator parses. After `step5c_main` calls `quiet_init`, `publish_core` `print()` routes to the quiet log, not a subprocess-captured stdout file, so a naive temp-file capture will miss `PLAN_WRITE_OK` and other rows needed for rc 1/3/4 stdout-authority parsing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Wrap publish_core in full stdout capture to the temp file (same pattern as step_final_summary_core render capture). Emit only allowlisted rows and disk-based markers on the contract stream afterward.
  - From Cursor-Requirements: Wrap publish_core with the same capture pattern used elsewhere in design_lifecycle (contextlib.redirect_stdout to a temp capture file, or _capture_contract_stream_to_paths). Parse that capture for read-result-env fallback. Emit step5c contract rows separately via emit_kv.

### FINDING_4: Plan stdout row list omits core orchestrator contract rows
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: The plan's enumerated Step 5c stdout row list (lines 65–74) omits `PUBLISH_RC`, `PLAN_WRITE_OK`, `PUBLISH_OK`, and `CLEANUP_ELIGIBLE`. After the background Step 5c task completes, the orchestrator cannot reliably branch on publish rc, plan-write failure, success footer, or cleanup eligibility from task output, regressing the current wrapper contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Add those four rows to the required emitted stdout rows and assert them in the Step 5c lifecycle tests.
