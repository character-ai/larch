### FINDING_1: Architectural-compliance focus mapping is missing
- **Reviewer(s)**: Codex-Arch, Codex-Innovation
- **Severity**: minor
- **Concern**: Static focus mapping does not recognize `architectural-compliance`, causing the specialist to be recorded as `code-quality` in `scout-archetype-yield.tsv` and downstream reviewer metrics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add architectural-compliance: architecture and cover the mapping.
  - From Codex-Innovation: Add architectural-compliance: architecture to _static_focus_area and test the mapping

### FINDING_2: Shared review-core stubs remain three-slot
- **Reviewer(s)**: Codex-Innovation
- **Severity**: minor
- **Concern**: Shared review-core stubs remain three-slot, so updated pipeline tests cannot exercise the new compliance slot and may report false coverage failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add the compliance slug to fixture outputs, manifests, and collector records
