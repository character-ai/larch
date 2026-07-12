### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/tests/report/test_final_report.py
- **Concern**: [SCOPE-REDUCTION] Keep _write_minimal_state as a raw sparse fixture instead of migrating it through write_session_env. Scenario: The plan both says to refactor _write_minimal_state via the shared writer and to retain deliberately incomplete session files. The helper baseline adds REPO_ROOT, plugin-root, and tool keys that minimal final-report tests currently omit; that can change report inputs beyond REPO=o/r.
- **Proposed resolution**: Exclude _write_minimal_state from shared-writer migration; keep its two-line raw session-env.sh. Use write_session_env only for ordinary plan-coverage setups that need the canonical baseline.
