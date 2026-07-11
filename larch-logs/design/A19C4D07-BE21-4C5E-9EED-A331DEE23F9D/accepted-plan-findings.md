### FINDING_1: Pre-work envelope validation blocks incremental coverage advancement
- **Reviewer(s)**: Codex-Arch, Codex-Innovation
- **Severity**: major
- **Concern**: Materialization validation requires the recorded `HEAD_SHA` and frozen diff to match the repository’s current commit before Piece 1 consumption can run. After a docs-only or CI-fix commit advances `HEAD`, the recorded materialization envelope still describes the covered commit, but this precondition rejects it before `note_consumable` or incremental coverage advancement can preserve the handled note. This breaks once-per-run re-entry behavior and can force unnecessary reassessment or failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Validate the recorded envelope against its own snapshot first, then delegate handled-state and incremental-diff decisions to Piece 1. Permit expected post-assessment `HEAD` movement for consumption and pre-filter re-entry; require a current-HEAD match only before a new launch and immediately before authored persistence.

