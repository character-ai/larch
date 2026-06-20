### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:3-7,19-25
- **Concern**: The plan bumps LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT via python/session_env.py _external_timeout in addition to LARCH_PROBE_TIMEOUT_SECONDS, but the binding issue scope recommends option (a): raise only the Step 0 probe default and defer the launch-time sibling knob unless operators report launch-time false-fails.. Scenario: The issue motivation and false-negative degraded gate are driven by check_reviewers per-attempt LARCH_PROBE_TIMEOUT_SECONDS (python/agents.py:956). Expanding to session_env.py, extra docs bullets, and new python/test_session_env.py coverage ships behavior and test surface the issue did not ask for and explicitly set aside.
- **Proposed resolution**: [SCOPE-REDUCTION] Limit file edits to python/agents.py, docs/configuration-and-permissions.md (LARCH_PROBE_TIMEOUT_SECONDS only), and python/test_agents.py. Drop the ### UPDATED: python/session_env.py section, the LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT doc changes, and the planned python/test_session_env.py _external_timeout tests unless the issue scope is widened to option (b).

### FINDING_9:
- **Reviewer(s)**: Codex-dyn-Semantics Guard
- **Severity**: important
- **Focus area**: correctness
- **Location**: larch-logs/design/091F33CE-13BA-4445-90A9-7366AD354D25/plan.txt:75-85; python/agents.py:947-956
- **Concern**: Plan can pass health timeout 0 into check_reviewers, where 0 is normalized through probe-timeout fallback semantics.. Scenario: LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT=0 can still become a 30 second probe via probe_timeout_seconds or _env_int(... zero_allowed=False), violating the health knob zero opt-out.
- **Proposed resolution**: Require the health resolver to short-circuit on exact 0 before calling check_reviewers, and pass only positive timeout values as probe_timeout_seconds.

### FINDING_10:
- **Reviewer(s)**: Codex-dyn-Semantics Guard
- **Severity**: nit
- **Focus area**: correctness
- **Location**: larch-logs/design/091F33CE-13BA-4445-90A9-7366AD354D25/plan.txt:136-180; python/test_agents.py:1042-1070
- **Concern**: Tests cover bad probe timeout only, not empty or zero, and do not assert health timeout zero opt-out.. Scenario: A shared parser could make both knobs use one zero rule and these tests would still pass.
- **Proposed resolution**: Add cases for LARCH_PROBE_TIMEOUT_SECONDS empty and 0 falling back to 30, plus LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT=0 skipping the health gate.
