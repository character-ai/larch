### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/lint/lint_monkeypatch_facade_binding.py
- **Concern**: [SCOPE-REDUCTION] Persist defining_module in baseline JSON.. Scenario: defining_module is derived metadata (like lineno in tempfile lint); storing it in baseline records adds churn on import reshuffles without changing the violation identity.
- **Proposed resolution**: Keep defining_module on live Finding stderr output only; exclude it from Record / BASELINE_KEYS and from serialize_baseline rows.
