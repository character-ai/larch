### FINDING_2: [OUT_OF_SCOPE] Step 3.5 continuation still uses the retired immediate-background contract
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, dyn-dyn-bgjob-step3
- **Severity**: major
- **Concern**: The Step 3.5 continuation prose still points orchestrators at the old immediate-background/task-notification recovery flow instead of the migrated bgjob start/wait/result-env contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: `Update Step 3.5 continuation to the same bgjob start/wait/BGJOB_RC contract (deferred chunk).`
  - From codex-specialist-correctness: `Replace the paragraph with the bgjob resume contract: foreground wrapper start or live-registry rejoin, repeated bgjob wait, and routing only after DONE with BGJOB_RC=0 plus required KVs.`
  - From cursor-specialist-edge-cases: `Replace with the same bgjob start/rejoin and chunked bgjob wait instructions used in the Step 3 launch and resume fences; add a test-design-structure.sh not_contains pin.`
  - From cursor-specialist-edge-cases: `Add a not_contains assertion for run_in_background on the Step 3.5 continuation path.`
  - From dyn-dyn-bgjob-step3: `Rewrite the Step 3.5 continuation bullet to match the Step 3 bgjob start/rejoin + chunked bgjob wait + `BGJOB_RC=0` + result-env parsing contract, and pin the absence of `run_in_background` / `<task-notification>` in that subsection in `scripts/test-design-structure.sh`.`


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_3: [OUT_OF_SCOPE] Step 3 wrapper regression coverage is missing for rejoin and failure paths
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing, dyn-dyn-bgjob-step3
- **Severity**: major
- **Concern**: The Step 3 wrapper’s runtime regression coverage was thinned out enough that live-registry rejoin, non-success DONE paths, and prior detach/signal/reattach scenarios can regress without a harness catching them.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: `Restore targeted runtime cases or relocate to integration harness.`
  - From cursor-specialist-testing: `Add a harness subtest that leaves a live registry row and asserts the second wrapper call execs bgjob wait instead of emitting STARTED.`
  - From cursor-specialist-testing: `Extend the fake bgjob wait stub and add subtests for each failure BGJOB_RC with assertions that success routing KVs are absent.`
  - From cursor-specialist-testing: `Reintroduce terminal-failure and missing-result wrapper tests through the bgjob fake plugin and result-env merge path.`
  - From cursor-specialist-testing: `Add a fake live-registry case that asserts the wrapper reuses `bgjob wait` and does not relaunch.`
  - From dyn-dyn-bgjob-step3: `Address the concern above.`


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_4: [OUT_OF_SCOPE] bgjob-migration docs/comments still mention legacy task-notification behavior
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing, dyn-dyn-bgjob-step3
- **Severity**: minor
- **Concern**: Several comments and guidance snippets still describe the pre-bgjob task-notification / EXIT-trap flow, which can mislead maintainers during follow-up cleanup.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: `Update comments to bgjob child + step3_wrapper_write_completed_step3_only behavior.`
  - From cursor-specialist-testing: `Revisit when making synthesis bgjob-aware; not blocking current happy path.`
  - From cursor-specialist-testing: `Update comments in a docs-only follow-up.`
  - From dyn-dyn-bgjob-step3: `Address the concern above.`


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_10: [OUT_OF_SCOPE] Sentinel-only continuation is unsafe if the daemon always writes the terminal marker
- **Reviewer(s)**: dyn-dyn-bgjob-step3
- **Severity**: minor
- **Concern**: The daemon writes `.completed/step-3-terminal` on every child exit, so callers that still trust the sentinel by itself can advance too early on mid-loop exits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-bgjob-step3: `Address the concern above.`
Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

