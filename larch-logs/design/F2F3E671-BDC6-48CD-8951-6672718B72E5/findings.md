### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/checks.py:475-477
- **Concern**: Plan extends the python/agents.py _DIRECT_TARGET_RULES row to py-test but leaves the python/design_lifecycle.py row routing only to test-check-plan-size. Scenario: Step 2b drafter dispatch moves into design_lifecycle.py; relevant-checks edits there will not run the new test_design_lifecycle.py CLI-verb assertions
- **Proposed resolution**: Add py-test (or wants_py_test=true) to the python/design_lifecycle.py / python/test_design_lifecycle.py tuple alongside or instead of test-check-plan-size-only routing

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/test_agents.py:24-51,320-332,1884-1885,3309-3310
- **Concern**: Deleting lib-external-launcher-common.sh while LIB_COMMON skipif parity tests remain. Scenario: Those tests use @pytest.mark.skipif(not LIB_COMMON.is_file()); after the lib is deleted they skip instead of failing, so startup-lock and classify_launch_failure parity can regress with a green py-test run
- **Proposed resolution**: Require explicit removal or Python replacement of every LIB_COMMON/bash-source parity branch in test_agents.py before migrated-scripts.tsv append; add a fail-closed assertion that no test_agents.py skipif references deleted script paths

### FINDING_3:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_agents.py:24-59
- **Concern**: Plan omits explicit removal of LIB_COMMON bash subprocess harnesses. Scenario: Deleting scripts/lib-external-launcher-common.sh leaves _bash_classify and _bash_startup_lock_acquire sourcing a missing file; py-test fails or skips parity silently
- **Proposed resolution**: make py-test

### FINDING_4:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/test_agents.py:24-47
- **Concern**: The `### UPDATED: python/test_agents.py` section does not explicitly retire existing `lib-external-launcher-common.sh` coupling (`LIB_COMMON`, `_bash_classify`, `_bash_startup_lock_acquire`, and skipif `test_parity_classify_*` / `test_startup_lock_blocks_bash_when_python_holds_shared_path`).. Scenario: After `scripts/lib-external-launcher-common.sh` is deleted and manifest-appended, `LIB_COMMON` path literals trip `make lint-retired-scripts`; bash-sourced parity tests skip via skipif and silently drop classifier/startup-lock coverage while CI stays green.
- **Proposed resolution**: Add explicit steps: remove `LIB_COMMON` and all bash-sourced helpers/tests; convert any still-needed assertions to pure-Python fixtures; include `python/test_agents.py` in the pre-delete retired-path `rg` sweep alongside `agent-lint.toml` and `python/checks.py`.

### FINDING_5:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/agents.py:1315-1333
- **Concern**: The plan ports bash `write_failure_diag` section order into `_compose_failure_diag` but does not state whether compose-time redaction stays or matches bash defer-redact-to-append semantics.. Scenario: Bash `write_failure_diag` composes unredacted sections; redaction runs at `append_vendor_failure_diagnostics`. Python `_compose_failure_diag` already redacts before write; expanding compose without an explicit rule can double-redact or shrink `vendor-failure-diagnostics` carriers vs retired bash/drafter behavior.
- **Proposed resolution**: State explicitly: either keep bash compose-unredacted + append-only redaction, or document intentional compose-time redaction and add a carrier fixture test that compares staged batch content to a pre-delete bash baseline.

### FINDING_6:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/test_design_cli_ports.py:31-40; plan.txt:255-258
- **Concern**: Agent drafter registry coverage is aimed at a machine-stdout-only test pattern. Scenario: Adding agent launch-codex-drafter or launch-claude-drafter to the existing EXPECTED table would also require _MACHINE_STDOUT_KEYS, setting LARCH_QUIET_DISABLE and changing quiet routing for launcher KVs and diagnostics
- **Proposed resolution**: Add a separate registry-only assertion for the new agent drafter verbs, and keep them out of _MACHINE_STDOUT_KEYS unless a targeted test proves quiet routing is intentionally disabled
