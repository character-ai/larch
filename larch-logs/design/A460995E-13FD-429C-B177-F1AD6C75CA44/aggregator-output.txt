### FINDING_1: Marker commit and rollback use the wrong repository root
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Concern**: Marker writes use ANALYSIS_ROOT, but the preserved commit and rollback commands still operate from PWD. With an explicit --root pointing to another checkout, write-state updates that checkout while git commit --only and rollback inspect PWD. The scan boundary may remain uncommitted, or the wrong repository may be modified.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Run the marker commit and rollback against ANALYSIS_ROOT, such as with git -C "$ANALYSIS_ROOT", and derive the marker path relative to that checkout.

### FINDING_2: Fix target grammar conflicts with filing reconciliation
- **Reviewer(s)**: Codex-Innovation, Codex-Requirements
- **Severity**: major
- **Concern**: Fix proposals initially use `fix:<stable-descriptive-token>` with `filed_issue: null`, while filing reconciliation attaches an issue number but then requires or implies an `issue:<number>` target. The reconciled record can become invalid under its own schema, block marker advancement, or violate the plan's immutable-content comparison.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: When attaching an issue number to a fix proposal, rewrite its target to issue:<number>, or define and validate one consistent target form that preserves the fix target while carrying filed_issue.
  - From Codex-Requirements: Keep `fix:<stable-descriptive-token>` valid after `filed_issue` is populated. Use the separate `filed_issue` field for GitHub adoption checks.

### FINDING_3: Stable proposal IDs are underspecified
- **Reviewer(s)**: Codex-Innovation
- **Severity**: minor
- **Concern**: Stable-ID construction remains underspecified despite the dedup fix. The plan requires a stable kebab-case ID derived from durable meaning but does not define canonical normalization, field ordering, or collision handling. Independent runs can produce different IDs for the same residual, or identical IDs for distinct proposals, defeating still-pending deduplication.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Specify one deterministic ID algorithm over normalized immutable proposal fields, including normalization and collision behavior, and use it in both proposal generation and reconciliation.
