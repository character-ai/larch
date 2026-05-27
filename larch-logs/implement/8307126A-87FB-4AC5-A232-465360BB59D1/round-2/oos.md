### FINDING_16: [OUT_OF_SCOPE] Plan voter path lacks `.done` barrier
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `dispatch-plan-voters.sh` has no equivalent voter `.done` barrier, leaving the same tally-before-complete class possible in the plan-review path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_17: [OUT_OF_SCOPE] Branch bundles unrelated script/test changes
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: The branch combines unrelated `#3007` script/test changes with the `#2973` voter fix, making review and revert isolation harder.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_18: [OUT_OF_SCOPE] Waterfall launcher also backfills missing `.done`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `dispatch-with-waterfall.sh` has a pre-existing missing-`.done` backfill pattern that may share the premature-sentinel failure class.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_19: [OUT_OF_SCOPE] Test hook env leakage can leave arbitrary source enabled
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: The pre-existing `LARCH_ALLOW_TEST_HOOKS` plus `LARCH_TEST_TRAP_AFTER_INNER_DONE_FILE` source hook can execute attacker-controlled code if those env vars leak into voter launch paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_20: [OUT_OF_SCOPE] Degraded quorum on sentinel timeout is an availability tradeoff
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: The wait intentionally proceeds after sentinel timeout, allowing tally with fewer judges; this is an availability/correctness tradeoff rather than a direct security flaw.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_21: [OUT_OF_SCOPE] Breadcrumb monitor can exit before review-and-fix finishes
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `breadcrumb-monitor.sh` can still let the orchestrator misread Step 5 completion and trigger redundant follow-up work while `review-and-fix` continues in the background.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_22: [OUT_OF_SCOPE] Lint-fix Codex path may misalign stall detection with events stream
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The lint-fix Codex path no longer uses `--capture-stdout` on `run-external-agent`, so wrapper stall detection may warn about an empty `codex.log` while events are written elsewhere.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

Vote tally: YES=2 NO=1 EXON=0 JUDGE_ERROR=0 Result=accepted

