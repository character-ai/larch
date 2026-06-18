### FINDING_1:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/agents.py:status_check_main (planned)
- **Concern**: status check port omits quiet_init / emit_kv contract that status.sh and other agent CLI mains use. Scenario: status.sh calls larch_quiet_init before emit_kv; /status SKILL parses machine KVs from stdout only. A status_check_main that uses plain print or stderr diagnostics can interleave non-KV lines and break KV parsing or skill rendering
- **Proposed resolution**: Add an explicit requirement: status_check_main must call logging_util.quiet_init and emit the eight contract keys only through logging_util.emit_kv (same pattern as check_reviewers_main / degraded_tools_gate_main)

### FINDING_2:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/plan_review.py:615-820, skills/design/scripts/review-design-step3-loop.sh:539-545
- **Concern**: Plan updates on-disk review-design-step3-loop.sh for write-design-round-meta cutover but omits regenerating the gzip _LEGACY_ASSETS blob that production Step 3 actually runs. Scenario: Live /design Step 3 delegates through plan_review._run_legacy(), which skips linking on-disk design/scripts (review-design-step3-loop.sh is in _RETIRE_DESIGN_SKIPS) and overwrites the materialized script from _LEGACY_ASSETS; deleting scripts/write-design-round-meta.sh while the stale embedded loop still defaults to that path leaves the -x gate false and post-revise round-meta.json refresh silently stops
- **Proposed resolution**: Add ### UPDATED: python/plan_review.py to regenerate the embedded skills/design/scripts/review-design-step3-loop.sh asset from the edited live script per docs/python-migration.md C3a1; keep test_embedded_review_design_step3_loop_matches_live_script passing

