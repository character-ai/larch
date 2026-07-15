---LARCH-REJECTED-BEGIN---
## Considered Plan Review Suggestions (Not Adopted)

These reviewer suggestions were considered but not adopted. Some may already be addressed by the current plan; they are not automatically unimplemented gaps.

### [Plan Review] FINDING_3

### FINDING_3:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: minor
- **Focus area**: code-quality
- **Location**: python/larch/lint/lint_self_disarmable_gate.py:main
- **Concern**: [SCOPE-REDUCTION] Remove the runtime Piece 1 API probe. Scenario: The issue is explicitly blocked on Piece 1, so a missing prepare_corpus surface cannot occur in the landed dependency graph; the probe and alternate exit-2 path add dead compatibility behavior.
- **Proposed resolution**: Rely on the declared dependency and construct the engine rule directly; retain the implementation-time dependency check only.

---LARCH-REJECTED-END---
