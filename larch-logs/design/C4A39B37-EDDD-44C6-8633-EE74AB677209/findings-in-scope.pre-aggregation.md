### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/design_lifecycle.py:step0_init_main
- **Concern**: Plan calls init_runparams_main in-process without stdout capture. Scenario: Bash design-step0-init.sh redirects design init-runparams stdout to a temp file and only surfaces read-result-env output; an in-process call prints INIT_STATUS/WARN/RENAMED KVs to the Step 0b fence stdout, changing orchestrator-visible output and quiet-mode behavior
- **Proposed resolution**: Mirror step0_route_main: subprocess python/cli.py design init-runparams with stdout captured to a temp file, parse .design-init-runparams-result.env via read-result-env semantics, and emit only the wrapper's existing stderr abort messages on failure

### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-step0-route.sh:101-121
- **Concern**: [SCOPE-REDUCTION] step0-route omits bash POSITIONAL_KIND re-validation block. Scenario: Invalid or stale POSITIONAL_KIND from parsed env can reach gh issue fetch or design route subprocess without the abort paths bash enforces today
- **Proposed resolution**: Mirror the issue/verbal/none/invalid case block from design-step0-route.sh in step0_route_main before issue fetch; add pytest for non-numeric issue positional and invalid POSITIONAL_KIND

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-step0-init.sh:137-176
- **Concern**: step0-init plan calls init_runparams_main in-process without stdout capture. Scenario: In-process init_runparams_main prints INIT_STATUS/WARN to wrapper stdout; bash captures stdout to a temp file and never relays it, so orchestrator/quiet parsing can see stray KVs
- **Proposed resolution**: Subprocess design init-runparams with stdout redirected to a capture file (bash parity) or call init_runparams_main with stdout suppressed; read .design-init-runparams-result.env only; pytest asserts wrapper stdout omits INIT_STATUS=

### FINDING_1:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/design_lifecycle.py:step0_session_main
- **Concern**: Inline parse stdout not specified when session runs parse before setup. Scenario: Step 0-pre bindings come from the Step 0a fence; bash prints parse KVs (STEP0_PARSED_ENV_PATH, PARTITION_REQUESTED, POSITIONAL_KIND, POSITIONAL_VALUE, etc.) before session setup (design-step0-session.sh:100-113). Plan only says inline the same validation paths, not relay stdout. Step 0b flag binding and verbal routing can silently use stale or empty argv state.
- **Proposed resolution**: In step0_session_main, when public argv is present, call step0_parse_main (or shared helper) and print its full KV stdout to the orchestrator before the combined session-setup stream; add pytest that session output includes parse KVs ahead of SESSION_TMPDIR.

### FINDING_1:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/design_lifecycle.py:step0_session_main
- **Concern**: Plan omits BOTH_DOWN_SEEN presence tracking for degraded-tools STEP0_STATUS. Scenario: Bash only treats BOTH_DOWN=false as one-down-with-prompted when BOTH_DOWN= was actually emitted; if Python keys only on BOTH_DOWN=false without that guard, a missing BOTH_DOWN line can yield needs-degraded-decision instead of degraded-one-down after Continue
- **Proposed resolution**: Port design-step0-session.sh:168-207: track whether BOTH_DOWN= appeared in gate output before the BOTH_DOWN=false plus .degraded-tools-gate-prompted branch; pin BOTH_DOWN_SEEN in scripts/test-design-structure.sh and python/test_design_lifecycle.py degraded-one-down-with-sentinel case

### FINDING_1:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/design_lifecycle.py (planned step0_session_main); skills/design/SKILL.md:258-304
- **Concern**: step0-session skips parse when argv is empty, so POSITIONAL_KIND=none is never materialized and a stale step0-parsed-$pid.env can be copied. Scenario: Running /design with no args after an earlier same-PID run can reuse stale issue/verbal flags or abort routing with invalid POSITIONAL_KIND, violating the no-positional contract
- **Proposed resolution**: Always run the shared parse path before session setup, even with zero argv; overwrite the parsed cache every run and add a zero-argv regression test

### FINDING_2:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/design_lifecycle.py (planned step0_session_main); python/session_env.py:795-799
- **Concern**: step0-session accepts --plugin-root but the plan does not require exporting it before session write-design-env. Scenario: If CLAUDE_PLUGIN_ROOT is expanded as a shell variable but not inherited in the environment, write-design-env with --claude-pid fails and design-run-$PPID.sh is not written
- **Proposed resolution**: Validate --plugin-root and set CLAUDE_PLUGIN_ROOT in the environment before invoking write-design-env or subprocess helpers; test with inherited CLAUDE_PLUGIN_ROOT absent

