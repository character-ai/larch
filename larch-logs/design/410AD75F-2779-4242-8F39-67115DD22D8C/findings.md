### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/stall_recovery.py:229-293
- **Concern**: Generic-profile classify port omits cmd_classify_generic_from_terminal_state semantics. Scenario: With --profile generic and --primary-state-file, bash validates terminal state, forces STALL_TRACKING=true and RESUME_HINT=none, hashes signatures with profile/skill_label, and emits DISPATCHER from SOURCE_SCRIPT; current classify() uses the implement path only, so /design terminal-state classification and Tier A/B dedup signatures diverge after shell deletion
- **Proposed resolution**: Add a dedicated generic branch (validate_terminal_state first) mirroring bash:1091-1112 signature seed, SOURCE_SCRIPT-based DISPATCHER, fixed RESUME_HINT/STALL_TRACKING, and generic artifact naming; cover in test_stall_recovery.py per plan line 127

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/stall_recovery.py:303-308
- **Concern**: Plan omits record_attempt append parity with bash cmd_record_attempt. Scenario: Current record_attempt replaces the attempts file with last_* keys only; bash atomically preserves prior rows and appends attempt.${count}.* fields. After shell deletion, case7 same-cause-repeat, multi-attempt Tier A/B tables, and any caller expecting durable attempt history break even if classify guard is fixed
- **Proposed resolution**: Add an UPDATED stall_recovery.py step: rewrite record_attempt to increment attempt_count in place, append attempt.N.{class,signature,resume_hint,outcome,utc} rows without dropping prior attempt.* entries, and add pytest parity for case7 (two failed classifies promote same-cause-repeat) plus attempt_count=2 after alternate outcome

### FINDING_3:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/stall_recovery.py:303-308
- **Concern**: Plan omits `record_attempt()` bash parity while deleting the shell body. Scenario: Current `record_attempt()` replaces the attempts file with flat `last_*` keys via `write_kvs()`, but bash appends `attempt.N.*` rows and `compose_report()` `_attempts_table()` only reads `attempt.{idx}.*` (lines 1436-1440). Harness cases 7/11/13/21 and Step 18a Tier A "full attempts" reports will show empty history after cutover
- **Proposed resolution**: Add a `record_attempt()` subsection mirroring bash `cmd_record_attempt` (lines 1309-1337): validate `--attempts-file` under tmpdir, increment `attempt_count`, append `attempt.N.{class,signature,resume_hint,outcome,utc}`, preserve prior rows; port harness case11/13/21 pytest coverage

### FINDING_4:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/stall_recovery.py:270-308
- **Concern**: Plan omits init-attempts and record-attempt parity while deleting the bash harnesses. Scenario: The current Python path writes only last_* fields, does not preserve attempt.N rows used by report tables, and lacks the bash attempts-file confinement checks, so retiring the bash harness can leave terminal reports with blank attempt rows and keep an out-of-tmpdir or symlink write path
- **Proposed resolution**: Add the minimal bash parity for init_attempts and record_attempt: validate attempts files under the tmpdir, preserve append-style attempt.N fields, emit the bash KVs, and port the existing init/record containment and stress cases before deleting the harnesses
