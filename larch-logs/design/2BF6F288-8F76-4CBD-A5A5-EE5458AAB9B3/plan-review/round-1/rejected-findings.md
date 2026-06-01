### [Plan Review] FINDING_5

### FINDING_5: Stall seed uses incomplete ship-pr-state.sh key set
- **Reviewer(s)**: Codex-dyn-state-contract
- **Severity**: important
- **Concern**: The fresh `seed-terminal-state` path proposes a six-key `ship-pr-state.sh`, but the canonical Step-8 contract requires the full `write_initial_state` key set (issue/repo identity, finalizer booleans, etc.). A pre-Step-8 stall with no existing state gets `SEEDED=true`, then `restore-finalize-state.sh` derives empty defaults and `implement-finalize.sh` cannot apply the `[STALLED]` title-prefix branch or flush the stalled run log to the correct run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-state-contract: Seed the existing canonical Step-8 state shape rather than the six-key subset, pulling ISSUE_NUMBER/RUN_ID/REPO/REPO_UNAVAILABLE and finalizer booleans from the same session/parent sources used by the current Step 5 seed or ship-pr write_initial_state contract; add the harness assertion for these rename-critical keys.


### [Plan Review] FINDING_8

### FINDING_8: write-final-report harness still documents retired Step 18 --print-stdout contract
- **Reviewer(s)**: Codex-dyn-harness-integration
- **Severity**: latent
- **Concern**: `test-write-final-report.sh` and its sibling doc still pin/describe the retired inline Step 18 conditional `--print-stdout` mirroring after emit logic moves to `step-18b-final-report.sh` without `--print-stdout`. Contradictory coverage can pass while no longer exercising the live Step 18 path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-harness-integration: Move the Step 18 emit matrix to test-step-18b-final-report.sh and retitle or trim the old cases/docs so test-write-final-report only covers write-final-report.sh interface behavior


