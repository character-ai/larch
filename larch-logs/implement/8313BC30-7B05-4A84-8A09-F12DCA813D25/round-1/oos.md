### FINDING_3: [OUT_OF_SCOPE] Voting-protocol docs still describe Claude-first voters
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: The shipped voting-protocol prose still describes the old Claude-first /design topology, so docs consumers can infer a voter layout that no longer matches runtime dispatch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_6: [OUT_OF_SCOPE] README still documents the old HARD role topology
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: minor
- **Concern**: README still presents the HARD panel as if it used the old uniform default-role topology, which can mislead operators about the current per-archetype substitution behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_7: [OUT_OF_SCOPE] Plan voter outputs are not round-scoped
- **Reviewer(s)**: cursor-specialist-edge-cases, dyn-dyn-voters
- **Severity**: minor
- **Concern**: Plan-review voter outputs still live at shared tmpdir basenames instead of round-specific paths, so multi-round runs can overwrite earlier outputs and leave stale classification rows pointing at the wrong file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-voters: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_8: [OUT_OF_SCOPE] Vendor-tool collapse hides semantic-label regressions
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: minor
- **Concern**: The tally path still rewrites or normalizes bare vendor tokens in a way that can hide semantic-label regressions, so renamed vote-output paths are not being enforced as the contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_10: [OUT_OF_SCOPE] Calibration harness still uses legacy voter labels
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: The design voter-calibration harness fixtures still use legacy Claude/Codex/Cursor labels, so semantic-label rows are not exercised in the harness path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_14: [OUT_OF_SCOPE] Fallback dispatch test omits stdout labels and cursor-tier prompt assertions
- **Reviewer(s)**: dyn-dyn-voters
- **Severity**: minor
- **Concern**: The Codex-down / Cursor-fallback dispatch test checks manifest shape and cursor-tier prompts, but it does not assert the emitted `VOTER_N_TOOL=cursor-*` labels or the prompt files passed into `_parse_rate_retry()`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-voters: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_15: [OUT_OF_SCOPE] Both-externals-down path mislabels unlaunched voters as failed
- **Reviewer(s)**: dyn-dyn-voters
- **Severity**: minor
- **Concern**: On the both-externals-down floor, voters 2/3 are emitted as `failed` with semantic default labels, while the agent voter flow uses `skipped` with empty paths for unlaunched slots, so telemetry and calibration consumers can diverge.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-voters: Address the concern above.
Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

