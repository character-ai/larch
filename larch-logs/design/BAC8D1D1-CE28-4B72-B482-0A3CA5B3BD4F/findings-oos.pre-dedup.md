### OOS_1:
- **Description**: [OUT_OF_SCOPE] Cleanup allowlist appears to preserve string-prefix root checks for rm -rf. Scenario: Current matcher accepts paths such as /tmp/../... before removal; this is pre-existing and not required to complete F2, but it is a data-loss hardening candidate
- **Reviewer**: Codex-Arch
- **Severity**: latent
- **Focus area**: security
- **Location**: scripts/cleanup-tmpdir.sh:35-53; plan.txt:22-24,48
- **Phase**: design

### OOS_1:
- **Description**: Stale persist-post-plan-keys.sh listed as approved writer. Scenario: Operators misread which writers remain after F2
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: AGENTS.md:65
- **Phase**: design

### OOS_1:
- **Description**: [OUT_OF_SCOPE] Inlining the full lib-design-tmpdir.sh validator while keeping the bash lib deferred duplicates ~176 lines that ~35 design scripts still source. Scenario: Validator logic can drift from scripts/lib-design-tmpdir.sh until the deferred-lib follow-up lands, causing write-design-env reject/accept to disagree with other design machinery on edge paths
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/session_env.py:27-27
- **Phase**: design

### OOS_2:
- **Description**: [OUT_OF_SCOPE] Linting doc still documents make test-session-env-roundtrip and other harnesses the plan deletes. Scenario: Operators following docs/linting.md hit stale targets until step-7 stale-reference sweep runs
- **Reviewer**: Cursor-Pragmatic
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: docs/linting.md:272-272
- **Phase**: design

### OOS_1:
- **Description**: Plan asserts `entry-gate` success KV is capturable under bash `$(…)` via `quiet_init`+`emit_kv` but only requires generic entry-gate pass/fail tests, not a shell-subprocess capture case mirroring `implement-bootstrap.sh:580-585` or `test_ship.py::test_quiet_init_routes_contract_and_breadcrumb_fds`. Scenario: Shared `logging_util.quiet_init` already has fd-3 coverage in ship tests; duplicate bash-capture test is optional hardening, not required for minimum-change F2
- **Reviewer**: Cursor-dyn-emitter-routing-fidelity
- **Severity**: nit
- **Focus area**: risk-integration
- **Location**: plan.txt:50-54 / python/test_session_env.py:74
- **Phase**: design

### OOS_2:
- **Description**: Per-verb emitter table classifies `write-id` as file-only silent success, but bash emits `FAILED=true`/`ERROR=` via `emit_kv` (fd 3) on usage errors and via `echo` (quiet log) on mkdir failure; verb prose mentions FAILED/ERROR but the table omits failure routing. Scenario: Current callers (`implement-bootstrap.sh:699`) ignore stdout and exit code on the happy path, so parity drift is latent unless a future caller captures failure KVs
- **Reviewer**: Cursor-dyn-emitter-routing-fidelity
- **Severity**: latent
- **Focus area**: correctness
- **Location**: plan.txt:57 / scripts/write-session-id.sh:32-44
- **Phase**: design

### OOS_3:
- **Description**: Plan asserts `entry-gate` KV is capturable under bash `gate_out=$(…)` but does not require a shell-subprocess capture test mirroring `implement-bootstrap.sh:580-585`; mitigation is implied via bash analogy only. Scenario: `logging_util.quiet_init` fd-3 behavior is already covered by `python/test_ship.py::test_quiet_init_routes_contract_and_breadcrumb_fds`; risk is regression-only
- **Reviewer**: Cursor-dyn-emitter-routing-fidelity
- **Severity**: nit
- **Focus area**: risk-integration
- **Location**: plan.txt:50-54 / python/test_session_env.py:74
- **Phase**: design

