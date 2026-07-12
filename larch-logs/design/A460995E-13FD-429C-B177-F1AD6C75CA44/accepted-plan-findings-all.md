### FINDING_1: Default-mode marker write occurs before proposal reconciliation
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-Proposal State Auditor
- **Severity**: major
- **Concern**: The default-mode flow still writes and commits marker state immediately after report generation, before reconciled proposal JSONL exists, and omits `--proposals-file`. Checked statuses and new residual proposals therefore may not persist.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add an explicit Step 4 sub-step to build the reconciled proposals JSONL after the report, then extend the existing write-state bash fence with --proposals-file pointing at that file before the marker-only commit
  - From Codex-Arch: Add `--proposals-file "$RECONCILED_PROPOSALS_PATH"` to the default-mode command and require the command to validate that the file is the checked-history-plus-new-proposals artifact.
  - From Cursor-Innovation: Move the default-mode `write-state`/`git commit --only` fence to after adoption rendering and reconciled JSONL assembly; pass `--proposals-file` and `--root "$ANALYSIS_ROOT"`; remove the pre-reconciliation marker write.
  - From Cursor-Pragmatic: Relocate or extend the default-mode subsection: build reconciled proposals JSONL after report sections 4-8, then call write-state with --proposals-file pointing at that file before the existing marker-only git commit.
  - From Cursor-Requirements: Explicitly rewrite the default-mode Step 4 marker subsection so write-state and git commit --only run once, only after building the reconciled proposals JSONL, and always pass --proposals-file.
  - From Cursor-dyn-Proposal State Auditor: Relocate the default-mode write-state/git commit --only block to after reconciled proposals JSONL is assembled; pass --proposals-file; forbid marker commit before Step 4 reconciliation completes


### FINDING_5: Proposal target encoding and adoption evidence are underspecified
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Codex-Requirements, Cursor-dyn-Proposal State Auditor
- **Severity**: major
- **Concern**: The plan does not define canonical `target` values or lookup rules for lint, hook, test, invariant, and guideline proposals. In particular, IDs alone may not identify the file or heading to inspect, while hook entries lack stable named IDs. Implementations could disagree about whether a proposal is adopted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Document and validate canonical target values per type in SKILL.md and the JSONL loader (for example CLI lint slug, repo-relative module path, hooks.json command basename, test path or path::function), and add fixture cases for each format
  - From Cursor-Innovation: Document one target format per type in schema v2 (aligned with `CoverageIndex` stems and `hooks/hooks.json` matching rules) and validate targets in the JSONL loader.
  - From Cursor-Pragmatic: Document one canonical target format per type in schema v2 (e.g., hook: hooks.json-relative command basename; lint: cli registration name; test: repo-relative path with optional ::test_name) and require SKILL residual authoring to emit that form.
  - From Codex-Requirements: Define the canonical `target` grammar and lookup algorithm for each proposal type. For invariant and guideline records, specify how both the document and the ID or heading are derived without adding an unstated schema field.
  - From Cursor-dyn-Proposal State Auditor: Document hook proposal target format in schema v2 docs and implement matching by exact hooks.json command path or matcher token with fixture tests for present and absent


### FINDING_8: Proposal-derived filesystem targets are not explicitly confined to the repository
- **Reviewer(s)**: Codex-Innovation, Codex-Requirements, Cursor-dyn-Proposal State Auditor
- **Severity**: major
- **Concern**: Adoption checks consume untrusted marker data and may read lint modules, tests, documents, or hook-related paths. Without rejecting absolute paths, traversal, and symlink escapes, a crafted target could probe outside `root`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Validate and resolve every filesystem target beneath `root` before reading it. Reject absolute paths, traversal, symlink escapes, and targets that do not match the expected path form for their proposal type.
  - From Codex-Requirements: Require path-bearing targets to be normalized relative paths beneath the resolved repository root. Reject absolute paths, traversal, and symlink escapes before any existence check or file read, and add focused rejection tests.
  - From Cursor-dyn-Proposal State Auditor: Resolve every repository-backed target relative to root, reject .. escapes and absolute paths before reads, and test rejection of traversal targets


### FINDING_11: Filing mode does not persist refreshed state when there are zero residuals
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Concern**: The filing branch can stop when deduplication leaves nothing to file, preventing adoption-status updates and scan-boundary persistence even though `check-proposals` succeeded.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Replace the zero-residual stop with a marker path that still reconciles checked proposals, calls write-state --proposals-file, and commits only the marker when check-proposals succeeded even if /issue is skipped.


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


