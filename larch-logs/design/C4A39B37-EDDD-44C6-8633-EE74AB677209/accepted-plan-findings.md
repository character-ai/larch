### FINDING_1: init_runparams in-process stdout leaks orchestrator contract
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: important
- **Concern**: The plan calls `init_runparams_main` in-process without capturing stdout. Bash `design-step0-init.sh` redirects `design init-runparams` stdout to a temp file and surfaces only `read-result-env` output; an in-process call prints `INIT_STATUS` / `WARN` / `RENAMED` KVs on the Step 0b fence stdout. That changes orchestrator-visible output and quiet-mode parsing behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Mirror step0_route_main: subprocess python/cli.py design init-runparams with stdout captured to a temp file, parse .design-init-runparams-result.env via read-result-env semantics, and emit only the wrapper's existing stderr abort messages on failure
  - From Cursor-Innovation: Subprocess design init-runparams with stdout redirected to a capture file (bash parity) or call init_runparams_main with stdout suppressed; read .design-init-runparams-result.env only; pytest asserts wrapper stdout omits INIT_STATUS=


### FINDING_2: Session inline parse stdout relay unspecified
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: When `step0_session_main` runs parse before session setup, the plan does not specify relaying parse stdout. Step 0-pre bindings are expected from the Step 0a fence; bash prints parse KVs (`STEP0_PARSED_ENV_PATH`, `PARTITION_REQUESTED`, `POSITIONAL_KIND`, `POSITIONAL_VALUE`, etc.) before session setup. An inline port that validates argv without relaying those KVs can leave Step 0b flag binding and verbal routing on stale or empty argv state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: In step0_session_main, when public argv is present, call step0_parse_main (or shared helper) and print its full KV stdout to the orchestrator before the combined session-setup stream; add pytest that session output includes parse KVs ahead of SESSION_TMPDIR.


### FINDING_3: BOTH_DOWN_SEEN guard missing for degraded-tools STEP0_STATUS
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The plan omits `BOTH_DOWN_SEEN` presence tracking for degraded-tools `STEP0_STATUS`. Bash only treats `BOTH_DOWN=false` as one-down-with-prompted when a `BOTH_DOWN=` line was actually emitted. Python that keys only on `BOTH_DOWN=false` without that guard can emit `needs-degraded-decision` instead of `degraded-one-down` after an explicit Continue.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Port design-step0-session.sh:168-207: track whether BOTH_DOWN= appeared in gate output before the BOTH_DOWN=false plus .degraded-tools-gate-prompted branch; pin BOTH_DOWN_SEEN in scripts/test-design-structure.sh and python/test_design_lifecycle.py degraded-one-down-with-sentinel case


### FINDING_4: Zero-argv session can reuse stale parsed-env cache
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: If `step0-session` skips parse when argv is empty, `POSITIONAL_KIND=none` is never materialized and a stale `step0-parsed-$pid.env` can be copied forward. Running `/design` with no args after an earlier same-PID run can reuse stale issue/verbal flags or abort routing with invalid `POSITIONAL_KIND`, violating the no-positional contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Always run the shared parse path before session setup, even with zero argv; overwrite the parsed cache every run and add a zero-argv regression test


### FINDING_5: --plugin-root not exported before write-design-env
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: `step0-session` accepts `--plugin-root`, but the plan does not require exporting it before `session write-design-env`. If `CLAUDE_PLUGIN_ROOT` is expanded as a shell variable but not inherited in the environment, `write-design-env` with `--claude-pid` can fail and `design-run-$PPID.sh` is not written.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Validate --plugin-root and set CLAUDE_PLUGIN_ROOT in the environment before invoking write-design-env or subprocess helpers; test with inherited CLAUDE_PLUGIN_ROOT absent


### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-step0-route.sh:101-121
- **Concern**: [SCOPE-REDUCTION] step0-route omits bash POSITIONAL_KIND re-validation block. Scenario: Invalid or stale POSITIONAL_KIND from parsed env can reach gh issue fetch or design route subprocess without the abort paths bash enforces today
- **Proposed resolution**: Mirror the issue/verbal/none/invalid case block from design-step0-route.sh in step0_route_main before issue fetch; add pytest for non-numeric issue positional and invalid POSITIONAL_KIND


