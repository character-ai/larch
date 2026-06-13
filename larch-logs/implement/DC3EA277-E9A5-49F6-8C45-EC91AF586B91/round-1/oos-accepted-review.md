### OOS_1: [OUT_OF_SCOPE] ship-pr runtime tests skip `run_checks_with_lint_fix_loop` wrapper path
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: New runtime lint-handoff tests in `scripts/test-ship-pr-rebase.sh` source `ship-pr.sh` and exercise `run_captured_cmd_then_fix_loop` plus `_rcc_handle_fix_status`, but duplicate the ledger handoff block (`rcc_main_agent_required_detail_log` → `emit_ship_pr_ledger_ready` → `exit_ship_pr_internal_lint_fix_handoff`) inline instead of calling `run_checks_with_lint_fix_loop`. A regression that removes or reorders handoff in that wrapper could still pass these tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add a case that stubs only `run_lint_fix_loop_capture` / `failure_capture_path` and drives `run_checks_with_lint_fix_loop` end-to-end.
  - From cursor-specialist-testing-output.txt: Optionally add a fourth case that stubs run_checks_with_lint_fix_loop internals and asserts ledger KVs after the full wrapper returns main-agent-required.


