### [Plan Review] FINDING_3

### FINDING_3: Stable proposal IDs are underspecified
- **Reviewer(s)**: Codex-Innovation
- **Severity**: minor
- **Concern**: Stable-ID construction remains underspecified despite the dedup fix. The plan requires a stable kebab-case ID derived from durable meaning but does not define canonical normalization, field ordering, or collision handling. Independent runs can produce different IDs for the same residual, or identical IDs for distinct proposals, defeating still-pending deduplication.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Specify one deterministic ID algorithm over normalized immutable proposal fields, including normalization and collision behavior, and use it in both proposal generation and reconciliation.

