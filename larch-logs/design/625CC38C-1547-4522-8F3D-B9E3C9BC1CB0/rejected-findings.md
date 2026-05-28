### [Plan Review] FINDING_9

### FINDING_9: Backward-compatible v3 writer round-trip is not tested
- **Reviewer(s)**: Cursor-dyn-schema-migration-compat, Codex-dyn-schema-migration-compat
- **Severity**: important
- **Concern**: The proposed tests do not explicitly cover a legacy caller that passes only the original flags while the writer emits schema_version 3 with all new v3 fields present as null.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-schema-migration-compat, Codex-dyn-schema-migration-compat: Add a concrete test case that invokes write-run-params.sh with only --classification, --output, --partition-requested, --brainstorm-requested, and --manual-gate-b; assert schema_version == 3, old booleans round-trip, and has("design_classification_reason"), has("design_classification_source"), has("sketch_budget"), has("review_budget"), has("workflow_path") with each new field == null


### [Plan Review] FINDING_11

### FINDING_11: Flag-signature linter scan scope is inconsistent
- **Reviewer(s)**: Codex-dyn-linter-pattern-gap
- **Severity**: latent
- **Concern**: The planned flag-signature linter scope is described inconsistently across behavior, docs, and hook wiring, making the implemented scan surface ambiguous and potentially broader than the minimum-change contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-linter-pattern-gap: Pick one scope and state it identically in behavior, docs, and hook rationale; for SIMPLE prefer skills/*/SKILL.md unless reference-file coverage is required by an acceptance criterion


### [Plan Review] FINDING_12

### FINDING_12: Downstream `/design` fallbacks can still silently downgrade to HARD
- **Reviewer(s)**: Cursor-dyn-silent-fallback-completeness, Codex-dyn-silent-fallback-completeness
- **Severity**: important
- **Concern**: The plan removes only the Step 0b writer-failure downgrade, while later recovery paths can still proceed as HARD when `run-params.json` is missing, malformed, or stale. A SIMPLE run can still take HARD sketches, HARD reviewer emphasis, or HARD review-round caps despite the stated goal of preventing silent tier downgrade.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-silent-fallback-completeness, Codex-dyn-silent-fallback-completeness: Extend Section B minimally to fail closed inside /design when post-Step-0 run-params is absent or invalid, or explicitly update these fallback branches and add a missing/malformed run-params acceptance test alongside the planned happy SIMPLE repro.

