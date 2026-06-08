### OOS_1:
- **Description**: Retaining test-lint-readability-preamble as a pytest wrapper duplicates coverage already exercised by make py-test. Scenario: Same pytest module runs in shard 20 and again in the python-tests job; extra wall-clock only, not a functional gap.
- **Reviewer**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: risk-integration
- **Location**: Makefile:578-579 / .github/workflows/ci.yaml:592
- **Phase**: design

### OOS_1:
- **Description**: Historical note still cites scripts/lint-readability-preamble.sh as the fixed em-dash example. Scenario: Stale prose only; no runtime coupling once the bash linter is retired
- **Reviewer**: Cursor-dyn-consumer-sweep
- **Severity**: nit
- **Focus area**: risk-integration
- **Location**: scripts/lint-awk-multibyte-regex.md:6,27
- **Phase**: design

