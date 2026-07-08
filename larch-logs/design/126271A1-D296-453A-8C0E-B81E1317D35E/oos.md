### FINDING_1: Pin lexical scope and occurrence semantics
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Requirements
- **Severity**: major
- **Concern**: The lint’s binding resolution and occurrence numbering are underspecified, so a test can be matched against the wrong module or later baseline rows can be renumbered when earlier patches appear in the same lexical scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Increment occurrence only for findings that pass the import-only facade classifier, using the same nearest-scope lexical pre-order rules as docs/linting.md.
  - From Codex-Arch: Track bindings per lexical scope and resolve `Name` and dotted-string roots only against imports visible at the call site.
  - From Cursor-Requirements: State qualified_symbol is the dotted enclosing test function/class path and occurrence counts every resolved literal-attr monkeypatch.setattr on a repo module in lexical pre-order within that scope, including non-violations, before suppression and baseline filtering


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_3: Define Finding.key() and baseline identity fields
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Requirements
- **Severity**: major
- **Concern**: Baseline identity and qualified_symbol rules are still underspecified, so an implementer could include reason or defining_module in the key or invent ad hoc symbol nesting, breaking reason preservation and baseline stability across import refactors.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Document identity as (file, qualified_symbol, facade_module, attribute, occurrence) with reason and defining_module stored but excluded from the key; define qualified_symbol with the same nested def/class/module prefix rules as docs/linting.md.
  - From Cursor-Innovation: Add an explicit Finding.key() -> (file, qualified_symbol, facade_module, attribute, occurrence); keep defining_module and reason out of the key; document BASELINE_KEYS as those five fields plus reason only
  - From Cursor-Requirements: Specify Finding.key() explicitly, e.g. (file, qualified_symbol, facade_module, attribute, occurrence), keep defining_module and reason as stored-only fields, and mirror lint_tempfile_dir.py _record_key vs BASELINE_KEYS


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### OOS_1: Add monkeypatch-facade-binding ratchet to linting catalog
- **Description**: Add monkeypatch-facade-binding ratchet to linting catalog. Scenario: Other AST ratchets document scan surface, baseline identity, suppression comment, regen target, and pytest path in docs/linting.md. This feature wires Makefile and cli.py but the plan omits the catalog row operators use for ratchet semantics.
- **Reviewer**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: docs/linting.md
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### OOS_2: Import-only consumer-module patches such as monkeypatch.setattr(run_log_flush, "_commit_run", ...) match the rule but are valid per the issue suggested fix.
- **Description**: Import-only consumer-module patches such as monkeypatch.setattr(run_log_flush, "_commit_run", ...) match the rule but are valid per the issue suggested fix.. Scenario: Post-#6494 tests already use run_log_flush._commit_run as the effective patch; V1 will flag hundreds of correct lines and push most suppression work into a very large grandfather baseline.
- **Reviewer**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: python/tests/report/test_run_logs.py
- **Phase**: design




Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

### OOS_3: Register the new ratchet in docs/linting.md
- **Description**: Register the new ratchet in docs/linting.md. Scenario: Issue wiring does not require it, but operators discover baseline identity and regen targets from that file for every other AST ratchet
- **Reviewer**: Cursor-Requirements
- **Severity**: minor
- **Focus area**: architecture
- **Location**: docs/linting.md
- **Phase**: design

Vote tally: YES=0 NO=2 JUDGE_ERROR=1 Result=rejected Fileable=false

