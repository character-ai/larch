### FINDING_6: Avoid executing the session environment as shell code
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: major
- **Concern**: The adapter sources `plugin-root.env`, allowing a tampered session file to execute arbitrary commands before validation and bgjob launch. Parse and strictly validate only the expected `CLAUDE_PLUGIN_ROOT` assignment.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_14: [OUT_OF_SCOPE] Revert premature implement skill-surface and closure changes
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, codex-specialist-edge-cases, codex-specialist-testing, dyn-dyn-bgjob-identity
- **Severity**: major
- **Concern**: `skills/implement/SKILL.md` was modified despite the plan marking it out of scope, and the skill-closure baseline was changed as collateral. The reference comments and baseline churn should be deferred until the integration piece explicitly authorizes the route wiring.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Revert SKILL.md changes or update plan scope in Piece 4.
  - From cursor-specialist-edge-cases: Revert SKILL.md frontmatter edits and collateral closure baseline changes or amend the plan with an explicit SKILL.md update.
  - From cursor-specialist-testing: Revert SKILL.md and baseline changes in this piece defer to Piece 4
  - From codex-specialist-edge-cases: Keep the change only if required for integration; otherwise defer it to the integration piece.
  - From codex-specialist-testing: Revert the unrelated comments unless required by the repository closure mechanism.
  - From dyn-dyn-bgjob-identity: The edit is reference-only, but it violates the stated partition boundary.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_15: [OUT_OF_SCOPE] Improve dead-registry cleanup containment
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: Dead-registry unlink does not perform a Bash-side containment check before removal. Although the path originates from `registry.read_for`, add a containment check under the registry root.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Add containment check under registry root before rm.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_16: [OUT_OF_SCOPE] Align the harness registry stub with production layout
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: The harness registry stub path differs from the production global registry, so registry integration bugs may not be caught offline.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Stub production registry layout or add integration tests.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

### FINDING_17: [OUT_OF_SCOPE] Add missing symlink-swap publication guards
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: `publish_fail_closed_terminal` does not revalidate the `result.env` path type immediately before overwrite, leaving a possible symlink-swap window.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Re-run the same symlink/regular-file guards immediately before writing result.env.


Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_18: [OUT_OF_SCOPE] Add negative and reserved-key harness coverage
- **Reviewer(s)**: cursor-specialist-testing, codex-specialist-testing
- **Severity**: minor
- **Concern**: The harness lacks behavioral coverage for several protected-path and reserved-key cases, including symlinked merge/result env files and runtime daemon-reserved merge-key refusal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add negative tests for symlinked implement-step8-assessment.merge.env and .result.env
  - From codex-specialist-testing: Add behavioral symlink/non-regular-file cases for every protected path and exercise reserved-key rejection through child writes.
  - From cursor-specialist-testing: Add optional runtime negative write_merge_kvs test


Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_19: [OUT_OF_SCOPE] Avoid shared fake-cli replacement across harness scenarios
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: The harness overwrites a shared fake `cli.py` midway through the suite, making later cases depend on the replacement stub.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Refactor harness to use per-scenario stub hooks without global cli.py replacement


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

### FINDING_20: [OUT_OF_SCOPE] Register the assessment harness as a residual Bash path
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: `test-step-8-assessment.sh` is absent from `scripts/residual-bash-paths.txt`, unlike `test-step-8-ship`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add path when Makefile target lands


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_21: [OUT_OF_SCOPE] Preserve the explicitly scoped-correct implementation behavior
- **Reviewer(s)**: dyn-dyn-bgjob-identity
- **Severity**: minor
- **Concern**: The reviewed child-mode behavior invokes `architectural-assessment run` only under `--bgjob-child`, validates stdout coverage, and publishes the launch-time `ASSESSMENT_COVERED_FINGERPRINT` from merge env without post-run materialization re-hashing. This matches the reviewed plan paths and is retained as an out-of-scope observation rather than an actionable defect.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-bgjob-identity: Address the concern above.
Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false
