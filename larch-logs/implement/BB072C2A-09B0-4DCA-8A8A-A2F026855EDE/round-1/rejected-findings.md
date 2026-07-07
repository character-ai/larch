### [rejected] FINDING_6

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_6: collision regression harness needs real path mapping
- **Reviewer(s)**: codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing
- **Severity**: major
- **Concern**: The regression only checks hard-coded unique strings, not actual parallel starts or computed result-env writes, so a slug-collision bug could still pass CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_7: merge-env truncation and merge-result-env wiring are not pinned
- **Reviewer(s)**: cursor-specialist-testing, dyn-dyn-bgjob-contract
- **Severity**: major
- **Concern**: The harness never asserts per-lane `: > "$…_MERGE_ENV"` truncation or the `--merge-result-env` wiring, so stale merge envs could satisfy the wait gate even if the truncate-before-start contract is dropped.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add contains pins for Truncate prose, : > merge-env truncation, and --merge-result-env in both research-phase.md and validation-phase.md.
  - From dyn-dyn-bgjob-contract: Add contains checks for merge-env truncation (e.g. `: > "$RESEARCH_LANE_MERGE_ENV"`, `: > "$VALIDATION_CURSOR_MERGE_ENV"`, `: > "$VALIDATION_CODEX_MERGE_ENV"`) and a research-phase pin for validation-style “passed the gate” / exclude-failed-lanes language once §1.4 is corrected.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

