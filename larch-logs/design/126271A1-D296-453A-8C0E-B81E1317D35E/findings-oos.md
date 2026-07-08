### OOS_1: Add monkeypatch-facade-binding ratchet to linting catalog
- **Description**: Add monkeypatch-facade-binding ratchet to linting catalog. Scenario: Other AST ratchets document scan surface, baseline identity, suppression comment, regen target, and pytest path in docs/linting.md. This feature wires Makefile and cli.py but the plan omits the catalog row operators use for ratchet semantics.
- **Reviewer**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: docs/linting.md
- **Phase**: design



### OOS_2: Import-only consumer-module patches such as monkeypatch.setattr(run_log_flush, "_commit_run", ...) match the rule but are valid per the issue suggested fix.
- **Description**: Import-only consumer-module patches such as monkeypatch.setattr(run_log_flush, "_commit_run", ...) match the rule but are valid per the issue suggested fix.. Scenario: Post-#6494 tests already use run_log_flush._commit_run as the effective patch; V1 will flag hundreds of correct lines and push most suppression work into a very large grandfather baseline.
- **Reviewer**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: python/tests/report/test_run_logs.py
- **Phase**: design



### OOS_3: Register the new ratchet in docs/linting.md
- **Description**: Register the new ratchet in docs/linting.md. Scenario: Issue wiring does not require it, but operators discover baseline identity and regen targets from that file for every other AST ratchet
- **Reviewer**: Cursor-Requirements
- **Severity**: minor
- **Focus area**: architecture
- **Location**: docs/linting.md
- **Phase**: design



