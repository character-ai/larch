### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: plan.txt:55-63
- **Concern**: The pre-work envelope validation requires the materialized HEAD, frozen diff, and expected live diff to match the repository's current commit before invoking Piece 1 consumption helpers. This defeats the required incremental coverage-advance path. After a docs-only or logs-only HEAD advance, the materialization snapshot is necessarily stale, so the coordinator rejects it before `note_consumable` or `invariant_note_consumable` can inspect the incremental diff and preserve the handled note.. Scenario: Validate the original materialization envelope against its recorded snapshot before consumption, then let the Piece 1 helpers perform the post-HEAD incremental-diff check. Reserve current-HEAD validation for a new launch and the final persistence race check.
- **Proposed resolution**: 



### FINDING_2:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/architectural_assessment.py: materialization-envelope validation and re-entry ordering
- **Concern**: Materialization validation requires the recorded `HEAD_SHA` and frozen diff to match the repository's current commit before Piece 1 consumption can run. Scenario: After an assessment, a docs-only or CI-fix commit advances `HEAD`. The recorded materialization envelope still describes the covered commit, but this precondition rejects it before `note_consumable` or incremental coverage advancement can preserve the handled note. That breaks the specified once-per-run re-entry behavior and can force unnecessary reassessment or failure.
- **Proposed resolution**: Validate the recorded envelope against its own snapshot first, then delegate handled-state and incremental-diff decisions to Piece 1. Permit expected post-assessment `HEAD` movement for consumption and pre-filter re-entry; require a current-HEAD match only before a new launch and immediately before authored persistence.



