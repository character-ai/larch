### FINDING_11:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/design_lifecycle.py (planned _capture_contract_stream_to_paths); python/logging_util.py:103-134
- **Concern**: [SCOPE-REDUCTION] The fd-level capture wrapper is unnecessary and risk-bearing for the proposed pure-core split. Scenario: Core helpers are planned to avoid quiet_init and return or write KV lines explicitly, so fd 3 capture is not needed. A generic fd 1/2/3 save-redirect-restore helper can fail when fd 3 is absent in ordinary Python callers, and runtime probe writes can corrupt machine stdout or stderr.
- **Proposed resolution**: Remove the generic fd-capture framework. Make cores accept explicit stdout/stderr log paths or return rc plus KV/stderr data, then let Python callers write the existing log files directly. Keep fd restoration probes in tests only if retained.
