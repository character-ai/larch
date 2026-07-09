### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/report/statusline.py:33-60
- **Concern**: Reset routing depends on payload source but repo SessionStart hooks never consume it. Scenario: The plan gates deactivate on payload["source"] in startup|clear, yet scripts/sessionstart-health.sh and scripts/test-sessionstart-statusline.sh only use cwd/session_id payloads with no source field. If SessionStart stdin omits source, session_reset_progress no-ops on every event including startup and stale current pointers keep rendering old breadcrumbs.
- **Proposed resolution**: Split hooks/hooks.json statusline SessionStart into startup|clear vs resume|compact matchers (reset only on the first), or document and add a hook-harness fixture proving SessionStart stdin includes source before shipping.

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: scripts/sessionstart-statusline.sh:15-16
- **Concern**: python/larch/report/statusline_install.py:159-179. Scenario: [SCOPE-REDUCTION] New progress session-reset CLI plus a second hook Python call duplicates install-statusline stdin parsing
- **Proposed resolution**: install_statusline_main already reads SessionStart stdin once to resolve repo_root; adding progress session-reset forces a second interpreter, cli.py registry entry, and argv-order harness churn for the same payload. Call session_reset_progress(stdin_text) at the start of install_statusline_main (after the disable guard) and keep the hook as one python3 progress install-statusline pipe; retain deactivate_run in progress_file.py.
