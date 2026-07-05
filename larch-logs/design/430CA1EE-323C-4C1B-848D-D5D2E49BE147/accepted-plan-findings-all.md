### FINDING_1: Synthesized stale-fallback ledger must be marked ready
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-dyn-Repair Loop Contract
- **Severity**: blocking
- **Concern**: When `no-changes-stale` is synthesized, the loop can populate ledger fields but still leave `ledger_ready` false, so `_print_loop_ledger` emits nothing and stall-recovery misses the required escalation metadata.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In checks_repair_loop_main, only set action=main-agent-edit when the stale-fallback helper sets loop.ledger_ready=True via _resolve_ledger_failure_detail_log_path; otherwise keep NEXT_ACTION=stall and LOOP_STATUS=no-changes-stale
  - From Cursor-Pragmatic: In the no-changes-stale fallback helper, set loop.ledger_ready=True before _print_loop_ledger; add LINT_FIX_LEDGER_READY=true to the planned test assertions
  - From Cursor-dyn-Repair Loop Contract: In checks_repair_loop_main after synthesizing ledger fields for no-changes-stale fallback, set loop.ledger_ready=True. Add assert "LINT_FIX_LEDGER_READY=true" in to the step6 fallback test list alongside the other LINT_FIX_LEDGER_* assertions.


