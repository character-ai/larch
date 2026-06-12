### OOS_7: [OUT_OF_SCOPE] Stale stall-tracking layers can block escalation-success reporting
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-architecture-output.txt
- **Severity**: important
- **Concern**: `normalize-outcome` can treat a run as stalled after a successful handoff because it reads stale stall state from ambient or non-cleared layers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Pass explicit --in-memory-stall-tracking false from write-final-report.sh or remove ambient STALL_TRACKING fallback
  - From cursor-specialist-edge-cases-output.txt: Clear all four stall layers on handoff or document orchestrator obligation explicitly
  - From dyn-architecture-output.txt: On every script-to-main-agent handoff path (`exit_ship_pr_internal_lint_fix_handoff`, Python `NEEDS_USER_INPUT` terminal writes, and post-recovery `clear-stall`), clear or refresh **all** stall-tracking layers the gate reads, or narrow `normalize-outcome` so a handoff-cleared ship state overrides stale session/finalize flags when `EXIT_CODE=3` and bail reason is a ledger handoff token.


### OOS_8: [OUT_OF_SCOPE] ship-pr lint-fix handoff tests are grep-only
- **Reviewer(s)**: cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Bash ship-pr lint-fix handoff tests statically grep for tokens instead of executing the path, so ordering and `STALL_TRACKING=false` regressions could pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add hermetic ship-pr test asserting exit 3 handoff with STALL_TRACKING=false before waterfall.
  - From codex-specialist-testing-output.txt: Add a runtime fixture for ship-pr-internal lint-fix main-agent-required.


