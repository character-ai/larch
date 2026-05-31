### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/review-implement-step5-loop.sh:241-244
- **Concern**: Plan does not require capturing STDERR_TAIL_PATH before lint_out is removed. Scenario: Implementer may parse STDERR_TAIL_PATH only inside case branches after `rm -f "$lint_out"`, losing the KV and skipping caller-scope tail emit on step5 lint-fix failures
- **Proposed resolution**: Add an explicit plan step: parse STDERR_TAIL_PATH (and optional CODER_LOG_FILE fallback) into a variable during or immediately after `step5_parse_lint_capture_file`, before `rm -f "$lint_out"`, then call `emit_failed_agent_stderr_tail_larch_err` from that stem on terminal statuses

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/review-implement-step5-loop.sh:243-245
- **Concern**: Step5 deletes lint capture before tail stem can be read. Scenario: Plan says parse STDERR_TAIL_PATH from $lint_out on terminal failure, but the script removes $lint_out immediately after step5_parse_lint_capture_file (which only reads LINT_FIX_STATUS). Emitting in the case arms after rm -f leaves no capture file to parse; CODER_LOG_FILE fallback is absent on dispatch-failed.
- **Proposed resolution**: main-agent-required / failed / lint-fix terminal exits never surface stderr tails in Step 5 Extend step5_parse_lint_capture_file to stash STEP5_STDERR_TAIL_STEM from STDERR_TAIL_PATH (and optional CODER_LOG_FILE) while $lint_out still exists, then rm; call emit_failed_agent_stderr_tail_larch_err on that stem in each terminal case arm (or one shared helper) before step5_emit_final_envelope / exit 2.

### FINDING_3:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/review-implement-step5-loop.sh:241-245
- **Concern**: Plan instructs "parse STDERR_TAIL_PATH= from $lint_out when terminal failure" but $lint_out is deleted unconditionally at line 244 before any failure-status check occurs. Scenario: An implementer placing the parse inside the case arm at line 245+ (after the rm -f) operates on a deleted file; awk returns empty; STDERR_TAIL_PATH is lost; tail silently never surfaces to chat for the step5 path
- **Proposed resolution**: The plan should explicitly state: save STDERR_TAIL_PATH= to a local variable by parsing $lint_out BEFORE line 244's rm -f, e.g. add a line between step5_parse_lint_capture_file and rm -f; then use the saved variable in the failure case arm. The current prose "when step5_parse_lint_capture_file yields a terminal failure ... parse from $lint_out" is logically inverted relative to file lifetime.

### FINDING_4:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/ship-pr.sh:2728-2747
- **Concern**: Recovery waterfall gates `_surface_ci_stderr_tail` on `tier_rc -ne 0`, but `launch-codex-ci.sh` / `launch-cursor-ci.sh` always `exit 0` and encode agent failure in `LAUNCHER_EXIT` KV on stdout (discarded via `>/dev/null`). Scenario: Agent failure in recovery still leaves `${output}.stderr-tail` on disk (from `run-external-agent.sh`) while `tier_rc` stays 0, so the planned surfacing never runs and chat stays silent on a documented lane
- **Proposed resolution**: Surface when `${output}.stderr-tail` is non-empty after each tier attempt (or capture launcher stdout and treat non-zero `LAUNCHER_EXIT` like the CI fix-loop), not only when `tier_rc -ne 0`

### FINDING_5:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/review-implement-step5-loop.sh:47-57,241-244
- **Concern**: `step5_parse_lint_capture_file` is not specified to extract `STDERR_TAIL_PATH=`, but `$lint_out` is deleted at line 244 before the case switch where the plan says to surface the tail. Scenario: An implementer following the plan tries to "parse `STDERR_TAIL_PATH=` from `$lint_out`" at the failure case-switch (line 245+), but `rm -f "$lint_out"` at line 244 has already deleted the file. The value is irretrievably lost. The plan does not say to extend `step5_parse_lint_capture_file` to also extract `STDERR_TAIL_PATH=` into a new global (e.g. `STEP5_LINT_STDERR_TAIL_PATH`) during its single file-read pass, which is the only window before the rm
- **Proposed resolution**: Add to the plan: extend `step5_parse_lint_capture_file` to extract `STDERR_TAIL_PATH=` (and optionally `CODER_LOG_FILE=`) into a new global variable `STEP5_LINT_STDERR_TAIL_PATH` during the existing loop at lines 50-53, so the value survives `rm -f "$lint_out"` and is available at the failure case-switch

### FINDING_6:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/review-implement-step5-loop.sh:241-295
- **Concern**: Step5 lint-failure surfacing omits ship-pr parity guards. Scenario: Plan calls emit_failed_agent_stderr_tail_larch_err after parsing STDERR_TAIL_PATH/CODER_LOG_FILE from $lint_out while set -e is active (set -e at ~219). emit_failed_agent_stderr_tail_larch_err returns 1 when stem is empty or ${stem}.stderr-tail is missing (scripts/lib-failed-agent-stderr-tail.sh:186-188). Missing || true can abort the loop before step5_emit_final_envelope/flush; empty parsed stem uses tail_file .stderr-tail in cwd
- **Proposed resolution**: Match ship-pr.sh: only call emit when stem is non-empty; append || true; prefer STDERR_TAIL_PATH then non-empty CODER_LOG_FILE (same order as _surface_lint_fix_stderr_tail)
