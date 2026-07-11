### FINDING_4: Re-entry must use Piece 1 consumption and incremental-diff semantics
- **Reviewer(s)**: Codex-Arch, Cursor-Innovation, Cursor-Requirements
- **Severity**: major
- **Concern**: Exact-HEAD handled checks and full-diff reprocessing violate once-per-run behavior after CI-fix commits, rebases, or other out-of-scope HEAD movement.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Retain the previously covered HEAD from durable metadata, compute the incremental diff from that HEAD to the current HEAD, and run the deterministic pre-filter on that incremental diff. Preserve the existing note and outcome when the incremental paths are proven out of scope; launch only when the incremental diff intersects a relevant scope. Add tests for both cases
  - From Cursor-Innovation: Replace exact-HEAD handled checks with note_consumable / invariant_note_consumable (repo_root + base_ref aware); only launch when consumable is false; add a test mirroring test_coverage_advancement_docs_only_note_remains_consumable proving no launcher call after docs-only HEAD advance
  - From Cursor-Requirements: Define handled kinds by delegating to existing note/outcome validators in architectural_guidelines.py and ship_guidelines.py rather than re-deriving identity rules in the coordinator


### FINDING_10: Read-only Claude must not be responsible for creating the result payload
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Concern**: Granting Claude only Read access while requiring it to create a result file makes successful assessments impossible or causes them to fall back to unavailable.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Specify that the launcher captures Claude stdout and atomically writes it to a prevalidated result path without granting Claude write access. Then validate and parse that regular non-symlink file.


### FINDING_11: Authored persistence must preserve compose materialization metadata
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Concern**: Low-level implement-note writers may omit the validated `MATERIALIZE_ENV` identity fields already threaded by compose-assessment writers, breaking durable identity and re-entry checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: After agent success, persist through write_compose_assessment and write_invariant_compose_assessment or an equivalent that copies the validated per-kind MATERIALIZE_ENV metadata and re-checks HEAD before write


### FINDING_12: Unavailable fallbacks need durable identity for idempotent re-entry
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Concern**: An unavailable note without fingerprint, HEAD, base-reference, and diff-snapshot identity cannot be recognized as handled on re-entry, causing repeated launches.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Persist the covered fingerprint, HEAD, base reference, and diff snapshot identity with unavailable notes, or define and validate an equivalent unavailable identity artifact. Include tests that re-enter after an unavailable fallback and assert that no second launch occurs.


### FINDING_13: Deviation-log persistence must be part of handled-state guarantees
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Concern**: If the note and outcome are persisted before deviation logging fails, re-entry can treat the kind as fully handled and never retry the missing log append.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Persist or verify the deviation log before establishing the handled note-and-outcome postcondition, or include the required deduplicated log entry in handled-state validation and retry only that append without relaunching Claude


### FINDING_15: Invariant violations must not use guideline deviation logging
- **Reviewer(s)**: Cursor-dyn-Assessment Boundary Auditor
- **Severity**: major
- **Concern**: Routing invariant violations through `append_deviation_note` duplicates or mislabels guideline warnings and diverges from invariant ship-gate semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-Assessment Boundary Auditor: Limit append_deviation_note to guideline deviation results; persist invariant violations only via write_invariant_implement_note.


### FINDING_18: Claude should receive only a minimal evidence directory
- **Reviewer(s)**: Codex-dyn-Assessment Boundary Auditor
- **Severity**: major
- **Concern**: Granting Claude access to the entire implement tmpdir exposes session state, logs, environment material, prior outputs, and other potentially sensitive files.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-Assessment Boundary Auditor: Build a coordinator-owned evidence directory containing only the copied knowledge snapshots, frozen diff, prompt, and result path. Grant Read access only to that directory, keep unrelated tmpdir files outside the allowed directory, and verify the prompt does not expose broader paths.


### FINDING_22:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: security
- **Location**: python/larch/implement/architectural_assessment.py:production launcher
- **Concern**: [SCOPE-REDUCTION] Granting Read access to the entire implement tmpdir exceeds the agent's evidence needs. Scenario: The tmpdir contains orchestrator-owned session and recovery artifacts. Untrusted prompt or evidence can cause Claude to read and return unrelated sensitive state despite lacking write tools
- **Proposed resolution**: Create a dedicated non-symlink assessment evidence directory containing only the frozen diff and knowledge snapshots. Grant Read access only to that directory, and keep the launcher-owned result path outside the agent's readable grant


### FINDING_1: Pre-work envelope validation blocks incremental coverage advancement
- **Reviewer(s)**: Codex-Arch, Codex-Innovation
- **Severity**: major
- **Concern**: Materialization validation requires the recorded `HEAD_SHA` and frozen diff to match the repository’s current commit before Piece 1 consumption can run. After a docs-only or CI-fix commit advances `HEAD`, the recorded materialization envelope still describes the covered commit, but this precondition rejects it before `note_consumable` or incremental coverage advancement can preserve the handled note. This breaks once-per-run re-entry behavior and can force unnecessary reassessment or failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Validate the recorded envelope against its own snapshot first, then delegate handled-state and incremental-diff decisions to Piece 1. Permit expected post-assessment `HEAD` movement for consumption and pre-filter re-entry; require a current-HEAD match only before a new launch and immediately before authored persistence.

