### FINDING_1: Generic-profile `classify()` omits terminal-state path
- **Reviewer(s)**: Cursor-Arch
- **Severity**: blocking
- **Concern**: Python `classify()` always follows the implement merge path (`ship-pr-state.sh` / `finalize-state.sh` / `session-env.sh`) and an implement-style signature seed. Bash routes `--profile generic` with `--primary-state-file` through `cmd_classify_generic_from_terminal_state`: it validates terminal state first, forces `STALL_TRACKING=true` and `RESUME_HINT=none`, hashes signatures with `profile`/`skill_label`, and sets `DISPATCHER` from `SOURCE_SCRIPT`. After the shell body is deleted, `/design` terminal-state classification and Tier A/B dedup signatures diverge from bash behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add a dedicated generic branch (validate_terminal_state first) mirroring bash:1091-1112 signature seed, SOURCE_SCRIPT-based DISPATCHER, fixed RESUME_HINT/STALL_TRACKING, and generic artifact naming; cover in test_stall_recovery.py per plan line 127


### FINDING_2: `init_attempts` / `record_attempt` lack bash append-and-containment parity
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Codex-Generic
- **Severity**: blocking
- **Concern**: The plan targets retiring `stall-recovery-report.sh` while leaving `init_attempts` and `record_attempt` behaviorally incomplete. Current Python `record_attempt()` replaces the attempts file with flat `last_*` keys via `write_kvs()` instead of atomically preserving prior rows and appending `attempt.N.{class,signature,resume_hint,outcome,utc}`. Python `init_attempts()` also omits bash containment checks (`validate_tmpdir_write_file`), required `--attempts-file` handling, and stdout KVs (`ATTEMPTS_FILE`, `ATTEMPT_COUNT`). `compose_report()` `_attempts_table()` reads only `attempt.{idx}.*` rows, so harness cases 7/11/13/21, Step 18a Tier A "full attempts" reports, same-cause-repeat promotion, and multi-attempt history break after cutover even if the classify guard is fixed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add an UPDATED stall_recovery.py step: rewrite record_attempt to increment attempt_count in place, append attempt.N.{class,signature,resume_hint,outcome,utc} rows without dropping prior attempt.* entries, and add pytest parity for case7 (two failed classifies promote same-cause-repeat) plus attempt_count=2 after alternate outcome
  - From Cursor-Pragmatic: Add a `record_attempt()` subsection mirroring bash `cmd_record_attempt` (lines 1309-1337): validate `--attempts-file` under tmpdir, increment `attempt_count`, append `attempt.N.{class,signature,resume_hint,outcome,utc}`, preserve prior rows; port harness case11/13/21 pytest coverage
  - From Codex-Generic: Add the minimal bash parity for init_attempts and record_attempt: validate attempts files under the tmpdir, preserve append-style attempt.N fields, emit the bash KVs, and port the existing init/record containment and stress cases before deleting the harnesses

