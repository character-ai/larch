### FINDING_1: Step5 deletes lint capture before STDERR_TAIL_PATH can be used
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, unknown-slot
- **Severity**: important
- **Concern**: The plan tells implementers to parse `STDERR_TAIL_PATH=` (and optionally `CODER_LOG_FILE=`) from `$lint_out` on terminal Step 5 lint-fix failures, but the script unconditionally runs `rm -f "$lint_out"` immediately after `step5_parse_lint_capture_file`, which today only reads `LINT_FIX_STATUS`. Any parse deferred to the `case` arms at lines 245+ operates on a removed file, so the tail stem is lost and caller-scope stderr tails never surface for `main-agent-required`, `failed`, `lint-fix-failed`, and related terminal paths (including when `CODER_LOG_FILE` fallback would be needed on dispatch-failed).
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add an explicit plan step: parse STDERR_TAIL_PATH (and optional CODER_LOG_FILE fallback) into a variable during or immediately after `step5_parse_lint_capture_file`, before `rm -f "$lint_out"`, then call `emit_failed_agent_stderr_tail_larch_err` from that stem on terminal statuses
  - From Cursor-Innovation: main-agent-required / failed / lint-fix terminal exits never surface stderr tails in Step 5 Extend step5_parse_lint_capture_file to stash STEP5_STDERR_TAIL_STEM from STDERR_TAIL_PATH (and optional CODER_LOG_FILE) while $lint_out still exists, then rm; call emit_failed_agent_stderr_tail_larch_err on that stem in each terminal case arm (or one shared helper) before step5_emit_final_envelope / exit 2.
  - From unknown-slot: The plan should explicitly state: save STDERR_TAIL_PATH= to a local variable by parsing $lint_out BEFORE line 244's rm -f, e.g. add a line between step5_parse_lint_capture_file and rm -f; then use the saved variable in the failure case arm. The current prose "when step5_parse_lint_capture_file yields a terminal failure ... parse from $lint_out" is logically inverted relative to file lifetime.
  - From unknown-slot: Add to the plan: extend `step5_parse_lint_capture_file` to extract `STDERR_TAIL_PATH=` (and optionally `CODER_LOG_FILE=`) into a new global variable `STEP5_LINT_STDERR_TAIL_PATH` during the existing loop at lines 50-53, so the value survives `rm -f "$lint_out"` and is available at the failure case-switch


### FINDING_2: Recovery waterfall stderr surfacing keyed only on tier_rc
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: A planned recovery-waterfall step surfaces CI stderr tails only when `tier_rc -ne 0`, but `launch-codex-ci.sh` / `launch-cursor-ci.sh` always exit 0 and encode agent failure in `LAUNCHER_EXIT` on stdout, which the recovery loop discards via `>/dev/null`. Agent failure can still leave `${output}.stderr-tail` on disk from `run-external-agent.sh` while `tier_rc` stays 0, so the surfacing path never runs and chat stays silent on that lane.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Surface when `${output}.stderr-tail` is non-empty after each tier attempt (or capture launcher stdout and treat non-zero `LAUNCHER_EXIT` like the CI fix-loop), not only when `tier_rc -ne 0`


### FINDING_3: Step5 stderr emit lacks ship-pr parity guards under set -e
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Concern**: The plan calls `emit_failed_agent_stderr_tail_larch_err` after parsing tail metadata while `set -e` is active (restored at ~219 after the lint subprocess). `emit_failed_agent_stderr_tail_larch_err` returns 1 when the stem is empty or `${stem}.stderr-tail` is missing (`scripts/lib-failed-agent-stderr-tail.sh:186-188`). Without `|| true` and a non-empty stem guard (as in ship-pr’s lint-fix tail path), the loop can abort before `step5_emit_final_envelope` / flush; an empty parsed stem resolves the tail file to `.stderr-tail` in the current working directory.
- **Suggested revisions (informational for voters; coder decides)**:
  - From unknown-slot: Match ship-pr.sh: only call emit when stem is non-empty; append || true; prefer STDERR_TAIL_PATH then non-empty CODER_LOG_FILE (same order as _surface_lint_fix_stderr_tail)

