### [Plan Review] FINDING_1

### FINDING_1: Optional migration metadata lacks coverage
- **Reviewer(s)**: Codex-Arch
- **Severity**: minor
- **Concern**: Migration tests cover only identity and metric projection, so optional metadata such as `source_issue`, `reason`, or `operator_override` could be lost without detection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add a migration fixture with every optional field and assert the migrated output preserves them exactly 1. **[correctness] Optional migration metadata lacks direct coverage.** This is a risk-bearing migration path. Test exact preservation of `source_issue`, `reason`, and `operator_override`.


