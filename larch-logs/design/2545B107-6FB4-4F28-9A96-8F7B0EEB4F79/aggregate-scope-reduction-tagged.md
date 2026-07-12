### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/test_support.py:26-54
- **Concern**: [SCOPE-REDUCTION] strict_queue/default_queue duplicate existing RecordingRunner(strict=, default=) knobs. Scenario: RecordingRunner already exposes strict exhaustion and lenient synthetic success via constructor fields; piece 1 changes no consumers, so two classmethods add parallel API surface and extra tests without enabling migration or new behavior
- **Proposed resolution**: Limit piece 1 to ok/completed/repo_root plus tests that exercise RecordingRunner(responses=list(...), strict=True) and RecordingRunner(default=...) directly; add named constructors only when a later partition repoints callers
