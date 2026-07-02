### OOS_1: [OUT_OF_SCOPE] Frozen settle and Step 2b.5 dispatch dataclasses in design_session.py mix pure routing tables with session-env and phase-result-env writer concerns.
- **Description**: [OUT_OF_SCOPE] Frozen settle and Step 2b.5 dispatch dataclasses in design_session.py mix pure routing tables with session-env and phase-result-env writer concerns.. Scenario: A dedicated design_dispatch.py (or colocate with design_postplan.py) would narrow module coupling, but behavior is unchanged if helpers stay pure.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/larch/design/design_session.py:24-77
- **Phase**: design



### OOS_2: `STEP2B5_EXIT_RC` duplicates the `design step2b5` fence exit code; unlike settle, there is no wrapper action/rc disagreement check that needs a separate emitted rc.
- **Description**: `STEP2B5_EXIT_RC` duplicates the `design step2b5` fence exit code; unlike settle, there is no wrapper action/rc disagreement check that needs a separate emitted rc.. Scenario: Extra stdout/env key surface with no new routing behavior; more pins and allowlist churn for parity with settle without a settle-style disagreement guard.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: nit
- **Focus area**: architecture
- **Location**: python/larch/design/design_session.py:24-77
- **Phase**: design



### OOS_3: Registry smoke test omits design settle-next-action
- **Description**: Registry smoke test omits design settle-next-action. Scenario: New CLI verb may ship without EXPECTED/_MACHINE_STDOUT_KEYS smoke coverage already enforced elsewhere via test-design-structure.sh and test_cli.py
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: python/tests/design/test_design_cli_ports.py:8-29
- **Phase**: design



### OOS_4: [SCOPE-REDUCTION] Dispatch tables live in design_session.py
- **Description**: [SCOPE-REDUCTION] Dispatch tables live in design_session.py. Scenario: Plan places frozen settle/step2b5 dispatch dataclasses in the wrapper-env module, mixing unrelated responsibilities
- **Reviewer**: Cursor-dyn-Routing Parity
- **Severity**: nit
- **Focus area**: architecture
- **Location**: python/larch/design/design_session.py:24-77
- **Phase**: design



