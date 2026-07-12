---LARCH-REJECTED-BEGIN---
## Considered Plan Review Suggestions (Not Adopted)

These reviewer suggestions were considered but not adopted. Some may already be addressed by the current plan; they are not automatically unimplemented gaps.

### [Plan Review] FINDING_4

### FINDING_4: Fixed lifecycle ordering conflicts with Cursor review launches
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Concern**: The proposed global order runs authentication preflight before model resolution, while Cursor review production resolves model arguments and writes preflight artifacts before authentication-related steps. This can change failure paths and violate the required review argv contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add profile configurable phase ordering or split preflight into model-args and auth phases; register review-ask with model resolution before auth preflight while ci-write and implement-write keep auth before model args


### [Plan Review] FINDING_5

### FINDING_5: No shared exported descriptor registry is specified
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Concern**: Frozen vendor descriptors are defined without an exported descriptor table or lookup contract, leaving later fixer lanes without a shared selection surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add an immutable registry keyed by codex, cursor, and claude, then test registry uniqueness, lookup, and required capabilities.


### [Plan Review] FINDING_8

### FINDING_8:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: code-quality
- **Location**: python/larch/agents/_vendor.py
- **Concern**: [SCOPE-REDUCTION] Parallel process-result and model types duplicate allowlisted _types.py helpers. Scenario: _types.py already defines RunExternalAgentResult LaunchResult and ModelArgResult on the import allowlist; redefining them in _vendor.py adds dead parallel types and drift risk without changing piece-1 behavior
- **Proposed resolution**: Reuse RunExternalAgentResult for injected executor results ModelArgResult for model resolution output and LaunchResult where a terminal launch envelope is needed; reserve new _vendor.py dataclasses for descriptor table hooks and Claude parsed-envelope outcomes only


---LARCH-REJECTED-END---
