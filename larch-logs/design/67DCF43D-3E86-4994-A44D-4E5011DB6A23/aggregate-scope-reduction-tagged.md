### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/implement/scripts/stall-recovery-report.sh:208-280
- **Concern**: [SCOPE-REDUCTION] Plan requires clearing IMPLEMENT_STALL_TRACKING in session-env.sh but that key does not exist in the repo. Scenario: Implementer adds dead KV rewrite logic and a harness case for a nonexistent key; no runtime consumer reads IMPLEMENT_STALL_TRACKING (only STALL_TRACKING in session-env.sh)
- **Proposed resolution**: Drop IMPLEMENT_STALL_TRACKING from clear-stall and test-stall-recovery-report.sh; clear only STALL_TRACKING (and STALL_STEP) in session-env.sh

### FINDING_10:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/scripts/stall-recovery-report.sh:120-125
- **Concern**: [SCOPE-REDUCTION] Plan clears nonexistent IMPLEMENT_STALL_TRACKING. Scenario: Repo has no IMPLEMENT_STALL_TRACKING key; only STALL_TRACKING in session-env.sh. Extra rewrite path adds untested surface with no stated requirement
- **Proposed resolution**: Drop IMPLEMENT_STALL_TRACKING from clear-stall; clear only STALL_TRACKING and STALL_STEP in session-env.sh

### FINDING_11:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/scripts/write-final-report.sh:184-190
- **Concern**: [SCOPE-REDUCTION] Plan adds clear-stall before normalize-outcome in write-final-report.sh outside the recovery-success path. Scenario: A run with escalation evidence and a real later stall can have STALL_TRACKING cleared before Step 18a classifies it, causing false success reporting or skipped terminal stall handling
- **Proposed resolution**: Remove the write-final-report.sh clear-stall call; keep stale-layer clearing in the explicit success-after-recovery path only
