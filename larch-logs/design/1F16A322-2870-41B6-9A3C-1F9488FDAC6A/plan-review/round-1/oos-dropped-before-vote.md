### OOS_2: regen-complexity-baseline lacks an explicit REASON pass-through pattern
- **Description**: regen-complexity-baseline lacks an explicit REASON pass-through pattern. Scenario: Peer regen targets document `--initial-reason` in Make. Operators may not discover they must re-run with `--reason` after the first failure
- **Reviewer**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: architecture
- **Location**: Makefile:89-92
- **Phase**: design

### OOS_3: Debt-report tests are folded into an already large baseline test module
- **Description**: Debt-report tests are folded into an already large baseline test module. Scenario: 720-line plan concentrates gate, writer, override, dispatcher, and debt coverage in one file
- **Reviewer**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: python/tests/lint/test_lint_complexity_baseline.py
- **Phase**: design

