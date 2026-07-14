### OOS_1: No guidance on RecordingRunner vs subprocess fakes
- **Description**: No guidance on RecordingRunner vs subprocess fakes. Scenario: Future harness authors may duplicate fake-bin scaffolding inline instead of picking RecordingRunner (in-process) vs shell_fixtures (subprocess PATH).
- **Reviewer**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/test_support.py
- **Phase**: design



### OOS_2: Shell helpers not re-exported from test_support.py
- **Description**: Shell helpers not re-exported from test_support.py. Scenario: Consumers can import tests.support.shell_fixtures directly or use conftest fixtures; skipping test_support re-export is consistent with piece-1 scope.
- **Reviewer**: Cursor-Arch
- **Severity**: nit
- **Focus area**: architecture
- **Location**: python/test_support.py
- **Phase**: design



### OOS_3: Fail-closed default stderr/exit code prose is unspecified
- **Description**: Fail-closed default stderr/exit code prose is unspecified. Scenario: Tests will pin behavior; extra plan prose is not required for piece 1 to ship.
- **Reviewer**: Cursor-Arch
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: python/tests/support/shell_fixtures.py
- **Phase**: design



