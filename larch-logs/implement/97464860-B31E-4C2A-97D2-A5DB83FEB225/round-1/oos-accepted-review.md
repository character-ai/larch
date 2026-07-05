### OOS_1: malformed ballots are treated as empty instead of failing closed
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: _ballot_block_count swallows parse errors as zero blocks, which can make a non-empty ballot look empty and suppress voting.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Fail closed to panel-failed when parse_findings_text raises.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected (latent-rerouted)

### OOS_2: design security OOS can be published into committed run logs
- **Reviewer(s)**: codex-specialist-edge-cases, cursor-specialist-testing
- **Severity**: important
- **Concern**: Design security OOS is written to a top-level file that design log publish can commit, so a plan-review security OOS can appear in committed design run logs despite the private-only contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Exclude security-oos-observations.md from design log publish or store it in a non-published private location.
  - From cursor-specialist-testing: Add allowlist and write-round tests asserting oos.md is included and retired pre-vote artifacts are not.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### OOS_3: mixed security-sidecar runs can file publicly and still fail the checkpoint
- **Reviewer(s)**: dyn-dyn-oos-routing
- **Severity**: important
- **Concern**: Removing the early return when security-oos-observations.md is present lets oos file create the public unified issue and call _after_checkpoint, but disposition-checkpoint still hard-fails on the security sidecar, so mixed runs can file successfully while Step 9a.1 stays unstamped and ship remains blocked.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-oos-routing: Split the checkpoint: clear non-security disposition when oos-issues.ndjson and filed URLs cover accepted non-security blocks, and gate only the security sidecar on private SECURITY.md disposition (or route mixed batches through oos-pipeline before public filing). Add an integration test where the sidecar is present, non-security OOS files, and checkpoint/ship behavior is asserted end-to-end.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)
