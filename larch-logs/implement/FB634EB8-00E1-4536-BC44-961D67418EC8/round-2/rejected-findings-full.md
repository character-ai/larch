### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: Postbump preflight has dead or misleading branch fallback logic
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `postbump_preflight` contains a branch fallback that is effectively dead after successful `rev-parse`, adding noise and possibly obscuring detached-HEAD semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: Merge bash parity can silently skip when bash exists
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `python/test_merge_bash_parity.py` can skip when `merge-pr.sh` is missing and lacks a fail-closed gate comparable to finalize parity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=1

### [rejected] FINDING_22

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_22: Timing report attaches rounds by start time only
- **Reviewer(s)**: dyn-timing-ledger-output.txt
- **Severity**: important
- **Concern**: `scripts/timing-report.sh` attaches round rows when only `round_start` is inside the parent step interval, even though the contract requires both round start and end to be contained.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-timing-ledger-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_23

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_23: Implement round timing idempotency cannot supersede stale rows
- **Reviewer(s)**: dyn-timing-ledger-output.txt
- **Severity**: latent
- **Concern**: Implement timing rows are idempotent by round number only, unlike design’s superseding behavior, so any premature implement row could not be corrected on retry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-timing-ledger-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: `_rebase_no_push` duplicates rebase helper logic
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `python/finalize.py` duplicates fetch/ancestor/rebase/abort behavior instead of delegating to shared `rebase.py`, risking divergent semantics as rebase helpers evolve.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: Postmerge log finalization alias is not consistently used
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `finalize_postmerge_logs` is effectively a passthrough while callers such as `merge.py` still call `flush_logs_post`, weakening the intended centralized postmerge finalization contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

