### FINDING_7: [OUT_OF_SCOPE] Plugin-root environment is sourced as executable shell code
- **Reviewer(s)**: cursor-specialist-correctness, dyn-dyn-bgjob-identity
- **Severity**: minor
- **Concern**: `rehydrate_plugin_root` sources `plugin-root.env`, allowing a tampered session file to execute arbitrary commands before path validation or bgjob launch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From dyn-dyn-bgjob-identity: Parsing and validating only a `CLAUDE_PLUGIN_ROOT=` assignment would close that trust boundary.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_8: [OUT_OF_SCOPE] Skill-surface and closure-baseline changes are premature
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing, dyn-dyn-bgjob-identity
- **Severity**: minor
- **Concern**: `skills/implement/SKILL.md` and `python/skill-closure-baseline.json` were changed even though Step 8 route activation and skill-surface wiring are deferred to the integration piece.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-testing: Defer SKILL.md wiring to integration piece
  - From dyn-dyn-bgjob-identity: That collateral churn should wait for the integration piece.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_9: [OUT_OF_SCOPE] Dead-registry cleanup lacks path containment validation
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: Dead-registry unlinking does not verify that `REGISTRY_PATH` is contained under the expected `IMPLEMENT_TMPDIR/bgjob` directory before removing it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_10: [OUT_OF_SCOPE] Harness timeout-retry stubs can leak across scenarios
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: The timeout-retry block replaces the shared fake `cli.py` during the suite, so later cases may depend on the replacement stub unintentionally.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Split stubs per scenario or restore shared cli after overwrite


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_11: [OUT_OF_SCOPE] Assessment harness is missing from the residual Bash-path inventory
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: `test-step-8-assessment.sh` is absent from `scripts/residual-bash-paths.txt`, leaving the residual-path list incomplete when the harness is added to Makefile or CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add with Makefile target in Piece 4 or same PR
Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false
