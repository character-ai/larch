### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/design_lifecycle.py:86-88
- **Concern**: step_final_summary_main grouped with stage/failure mains that call quiet_init before delegating to core. Scenario: design-step-final-summary.sh never calls larch_quiet_init; markers and REPORT_GATE_SIDECARS_FILE must land on the background task stdout the orchestrator parses. quiet_init routes printable output to the quiet log and fd 3, so LARCH_FINAL_SUMMARY_BEGIN/END can disappear from task output.
- **Proposed resolution**: Carve step_final_summary_main out of the shared quiet_init CLI pattern: validate tmpdir, run step_final_summary_core, emit markers and sidecars on process stdout only; do not call logging_util.quiet_init in this verb.



### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/design_summary.py:372-375
- **Concern**: skills/design/scripts/design-step-final-summary.sh:113-117. Scenario: step_final_summary_core in-process render_final_summary_main call lacks stdout/stderr capture plan requires
- **Proposed resolution**: Shell redirects render-final-summary to render-final-summary.stdout.log then emits LARCH markers to real stdout render_final_summary_main writes full summary body and REPORT_GATE_SIDECARS_FILE to sys.stdout in-process call pollutes orchestrator stdout before markers and breaks marker extraction contract In step_final_summary_core capture render_final_summary_main stdout/stderr to $DESIGN_TMPDIR/render-final-summary.stdout.log (mirror shell redirect) then emit marked summary and sidecar handoff from disk only on real stdout/contract stream



### FINDING_3:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/plan_review.py:207-208
- **Concern**: python/plan_review.py:253-254. Scenario: Plan replaces shell staging with stage_terminal_state_core but leaves helper.exists() early returns
- **Proposed resolution**: Both step3_stage_postplan_failed and stage_panel_init_failed return 0 when design-stage-terminal-state.sh is missing. After hard delete, terminal state is never staged and sentinels are never written, silently breaking failed-postplan and panel-init-failed teardown. Remove helper path checks. Always call stage_terminal_state_core via _capture_contract_stream_to_paths. Preserve sentinel touch on rc 0 only.



### FINDING_4:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/design-step-final-summary.sh:110
- **Concern**: python/design_lifecycle.py step_final_summary_core. Scenario: Plan omits best-effort bg-wait marker start semantics
- **Proposed resolution**: Shell uses design_bg_wait_marker_start ... || true and still renders, emits markers, and writes .completed/step-final-summary when marker creation fails. A strict context manager that raises aborts final-summary on transient marker I/O failure. Mirror || true: log marker start failure, continue without .bg-wait-active, still run render, marked emission, sidecar handoff, and completion sentinel. Only skip marker when pause fires first.



### FINDING_5:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-step-final-summary.sh:113-118
- **Concern**: python/design_lifecycle.py step_final_summary_core. Scenario: Plan does not require redirecting render-final-summary stdout/stderr to render-final-summary.stdout.log
- **Proposed resolution**: Shell redirects render-final-summary to a log file. In-process render_final_summary_main also writes the full summary body to sys.stdout on post paths, which can leak into the parent contract stream or corrupt LARCH_FINAL_SUMMARY marker extraction. Capture render_final_summary_main stdout/stderr to design_tmpdir/render-final-summary.stdout.log (and stderr log if used), same as the shell redirect. Emit markers only via the disk helpers.



### FINDING_6:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-step-final-summary.sh:118-145
- **Concern**: python/design_lifecycle.py step_final_summary_core. Scenario: Plan does not pin non-fatal render failure before marked emission
- **Proposed resolution**: Shell records _render_final_summary_rc under set +e but always runs emit_final_summary_marked_from_disk, sidecar handoff, and touches .completed/step-final-summary regardless of render rc. After in-process render, always proceed to marked emission, sidecar handoff, flush, and completion sentinel even when render returns non-zero, matching current shell ordering.



### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/SKILL.md:534
- **Concern**: skills/design/references/decompose-panel.md:58. Scenario: Split-path retry-exhaustion prose still names deleted design-stage-terminal-state.sh without launcher or CLI path
- **Proposed resolution**: SKILL.md Step 2b.5 tells the orchestrator to invoke design-stage-terminal-state.sh directly. decompose-panel still shows an absolute deleted script path. Post-delete runs fail unless every caller is retargeted. Update SKILL.md line 534 and decompose-panel fence to the launcher basename design-stage-terminal-state.sh via design-run-$PPID.sh or python3 ... cli.py design stage-terminal-state with the same args and stdout/stderr capture.



### FINDING_8:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-design-structure.sh:71
- **Concern**: python/design_lifecycle.py. Scenario: Plan updates test-design-structure.sh generally but not the pinned clarify-hard-halt substring
- **Proposed resolution**: Harness currently requires design-stage-terminal-state.sh inside design_lifecycle.py. After in-process port that string disappears and make test-design-structure fails even when behavior is correct. Replace line 71 with an assertion for stage_terminal_state_core or _capture_contract_stream_to_paths wiring in step0_clarify_hard_halt_main.



### FINDING_9:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/design_lifecycle.py:86-88
- **Concern**: The plan applies quiet_init to all three CLI *_main wrappers, including step_final_summary_main. Scenario: design-step-final-summary.sh never sources lib-quiet.sh; it prints LARCH_FINAL_SUMMARY_BEGIN/END and REPORT_GATE_SIDECARS_FILE= on process stdout for Bash task-notification parsing. quiet_init redirects stdout to the quiet log, so the orchestrator loses markers and sidecar KVs after the port
- **Proposed resolution**: Exempt step_final_summary_main from quiet_init. Keep render output redirected to render-final-summary.stdout.log; emit markers and REPORT_GATE_SIDECARS_FILE= on real stdout exactly like the shell wrapper



### FINDING_10:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/design_lifecycle.py (planned step_final_summary_core); skills/design/scripts/design-step-final-summary.sh:112-118; python/design_summary.py:364-374
- **Concern**: step_final_summary_core calls render_final_summary_main in-process without preserving the shell stdout capture. Scenario: render_final_summary_main writes the unmarked final-summary body to stdout on post phase. The current wrapper redirects that output to render-final-summary.stdout.log before emitting LARCH_FINAL_SUMMARY_BEGIN/END. The proposed port can leak an unmarked body into task stdout and lose the existing log artifact.
- **Proposed resolution**: Capture only the render_final_summary_main stdout to $DESIGN_TMPDIR/render-final-summary.stdout.log before marked emission. Preserve current stderr behavior unless a test proves stderr capture is required.



### FINDING_11:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/design_lifecycle.py (planned _capture_contract_stream_to_paths); python/logging_util.py:103-134
- **Concern**: [SCOPE-REDUCTION] The fd-level capture wrapper is unnecessary and risk-bearing for the proposed pure-core split. Scenario: Core helpers are planned to avoid quiet_init and return or write KV lines explicitly, so fd 3 capture is not needed. A generic fd 1/2/3 save-redirect-restore helper can fail when fd 3 is absent in ordinary Python callers, and runtime probe writes can corrupt machine stdout or stderr.
- **Proposed resolution**: Remove the generic fd-capture framework. Make cores accept explicit stdout/stderr log paths or return rc plus KV/stderr data, then let Python callers write the existing log files directly. Keep fd restoration probes in tests only if retained.



