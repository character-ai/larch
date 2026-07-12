### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: code-quality
- **Location**: python/larch/agents/_vendor.py
- **Concern**: [SCOPE-REDUCTION] Parallel process-result and model types duplicate allowlisted _types.py helpers. Scenario: _types.py already defines RunExternalAgentResult LaunchResult and ModelArgResult on the import allowlist; redefining them in _vendor.py adds dead parallel types and drift risk without changing piece-1 behavior
- **Proposed resolution**: Reuse RunExternalAgentResult for injected executor results ModelArgResult for model resolution output and LaunchResult where a terminal launch envelope is needed; reserve new _vendor.py dataclasses for descriptor table hooks and Claude parsed-envelope outcomes only
