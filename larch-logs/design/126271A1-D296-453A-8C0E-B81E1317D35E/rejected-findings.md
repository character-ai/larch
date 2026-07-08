### [Plan Review] FINDING_2

### FINDING_2: Canonicalize facade_module identities
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: major
- **Concern**: The same facade can serialize under alias, chain, or module-path spellings, which will duplicate baseline identities and make one defect report inconsistently across tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Store facade_module as the canonical dotted module path from the resolved source file; keep import aliases and attribute-chain spellings diagnostic-only.
  - From Cursor-Innovation: Require facade_module to be the fully qualified module name of the resolved patch target (e.g. larch.report.run_logs), never the test-local import alias or attribute-chain prefix module.


### [Plan Review] FINDING_4

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/lint/lint_monkeypatch_facade_binding.py
- **Concern**: [SCOPE-REDUCTION] Persist defining_module in baseline JSON.. Scenario: defining_module is derived metadata (like lineno in tempfile lint); storing it in baseline records adds churn on import reshuffles without changing the violation identity.
- **Proposed resolution**: Keep defining_module on live Finding stderr output only; exclude it from Record / BASELINE_KEYS and from serialize_baseline rows.


