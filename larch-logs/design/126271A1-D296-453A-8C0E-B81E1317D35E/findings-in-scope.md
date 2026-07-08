### FINDING_1: Pin lexical scope and occurrence semantics
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Requirements
- **Severity**: major
- **Concern**: The lint’s binding resolution and occurrence numbering are underspecified, so a test can be matched against the wrong module or later baseline rows can be renumbered when earlier patches appear in the same lexical scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Increment occurrence only for findings that pass the import-only facade classifier, using the same nearest-scope lexical pre-order rules as docs/linting.md.
  - From Codex-Arch: Track bindings per lexical scope and resolve `Name` and dotted-string roots only against imports visible at the call site.
  - From Cursor-Requirements: State qualified_symbol is the dotted enclosing test function/class path and occurrence counts every resolved literal-attr monkeypatch.setattr on a repo module in lexical pre-order within that scope, including non-violations, before suppression and baseline filtering

### FINDING_2: Canonicalize facade_module identities
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: major
- **Concern**: The same facade can serialize under alias, chain, or module-path spellings, which will duplicate baseline identities and make one defect report inconsistently across tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Store facade_module as the canonical dotted module path from the resolved source file; keep import aliases and attribute-chain spellings diagnostic-only.
  - From Cursor-Innovation: Require facade_module to be the fully qualified module name of the resolved patch target (e.g. larch.report.run_logs), never the test-local import alias or attribute-chain prefix module.

### FINDING_3: Define Finding.key() and baseline identity fields
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Requirements
- **Severity**: major
- **Concern**: Baseline identity and qualified_symbol rules are still underspecified, so an implementer could include reason or defining_module in the key or invent ad hoc symbol nesting, breaking reason preservation and baseline stability across import refactors.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Document identity as (file, qualified_symbol, facade_module, attribute, occurrence) with reason and defining_module stored but excluded from the key; define qualified_symbol with the same nested def/class/module prefix rules as docs/linting.md.
  - From Cursor-Innovation: Add an explicit Finding.key() -> (file, qualified_symbol, facade_module, attribute, occurrence); keep defining_module and reason out of the key; document BASELINE_KEYS as those five fields plus reason only
  - From Cursor-Requirements: Specify Finding.key() explicitly, e.g. (file, qualified_symbol, facade_module, attribute, occurrence), keep defining_module and reason as stored-only fields, and mirror lint_tempfile_dir.py _record_key vs BASELINE_KEYS

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/lint/lint_monkeypatch_facade_binding.py
- **Concern**: [SCOPE-REDUCTION] Persist defining_module in baseline JSON.. Scenario: defining_module is derived metadata (like lineno in tempfile lint); storing it in baseline records adds churn on import reshuffles without changing the violation identity.
- **Proposed resolution**: Keep defining_module on live Finding stderr output only; exclude it from Record / BASELINE_KEYS and from serialize_baseline rows.
