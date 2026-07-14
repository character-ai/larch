### OOS_1: No guidance on RecordingRunner vs subprocess fakes
- **Description**: No guidance on RecordingRunner vs subprocess fakes. Scenario: Future harness authors may duplicate fake-bin scaffolding inline instead of picking RecordingRunner (in-process) vs shell_fixtures (subprocess PATH).
- **Reviewer**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/test_support.py
- **Phase**: design

