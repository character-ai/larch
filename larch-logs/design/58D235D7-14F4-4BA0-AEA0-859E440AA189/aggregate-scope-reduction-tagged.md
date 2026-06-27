### FINDING_9:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/larch/state/stall_recovery.py:571-620
- **Concern**: [SCOPE-REDUCTION] Keep the sidecar recovery out of generic prefixed classification. Scenario: The issue only asks for standard classify and Tier A compose-report recovery. Adding `_classify_generic_from_terminal_state()` and prefixed generic artifact scans broadens the fix into a new unneeded execution path.
- **Proposed resolution**: Drop the generic-prefixed sidecar branch unless a separate generic regression proves it is required

### FINDING_20:
- **Reviewer(s)**: Codex-dyn-Evidence Path Correctness
- **Severity**: blocking
- **Focus area**: security
- **Location**: <TMPDIR>/plan.txt:5-9,25-33
- **Concern**: [SCOPE-REDUCTION] Narrow the sidecar fallback to oversize-only cases. Scenario: At python/larch/state/stall_recovery.py:315-333, 513-567, and 571-630, the current code rejects non-absolute, symlink, outside-tmpdir, missing, unreadable, and oversize failure-detail logs before any read, and python/test_stall_recovery.py:1051-1079 locks that behavior in. The plan's broad "when that path is invalid, look in the ledger" wording would let classify() or _classify_generic_from_terminal_state() recover from malformed input via an unrelated sidecar instead of preserving the current fail-closed rejection path.
- **Proposed resolution**: Only consult the ledger after the direct path fails with oversize or truncation. Keep every other validation failure on the current hard-fail path.

### FINDING_21:
- **Reviewer(s)**: Codex-dyn-Evidence Path Correctness
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:21-24,29-33
- **Concern**: [SCOPE-REDUCTION] Do not let prefixed runs probe unprefixed ledgers. Scenario: At python/larch/state/stall_recovery.py:480-567 and 2180-2221, the proposed shared lookup can be used by implement classify() and Tier A compose-report, and the candidate list still names _DEFAULT_ESCALATION_LEDGER and _DEFAULT_ESCALATION_FALLBACK even when artifact_prefix is set. That makes a prefixed run vulnerable to stale unprefixed rows from another invocation, despite the prefix-scoped artifact expectations already asserted in python/test_stall_recovery.py:645-678 and 1599-1658.
- **Proposed resolution**: When artifact_prefix is set, restrict the helper to the prefixed ledger and fallback files for that run. Do not consult the unprefixed defaults, and keep row selection inside the active prefix scope.
