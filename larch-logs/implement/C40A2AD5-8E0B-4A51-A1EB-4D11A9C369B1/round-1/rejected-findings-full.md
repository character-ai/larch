### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: “Waits on wrapper sentinels” mis-describes synchronous Claude plan Voter 1 vs async waterfall slots
- **Reviewer(s)**: dyn-doc-claim-accuracy-output.txt
- **Severity**: important
- **Concern**: Copy reads like the async collector sentinel contract for all voters, but Voter 1 is launched synchronously (blocking on `launch-claude-review.sh` with `.done` normalization afterward), while “wait on sentinels” language better matches the `dispatch-with-waterfall.sh` path used for other slots.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-doc-claim-accuracy-output.txt: Describe Voter 1 as a blocking subprocess invocation whose completion implies the sidecars exist, and reserve "wait on sentinels" language for the `dispatch-with-waterfall.sh` path used for the other slots (`scripts/dispatch-plan-voters.sh:137-142`).


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: Informal “ballot aggregator” label without a concrete script name for operators
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Informal “ballot aggregator” wording does not map cleanly to the concrete aggregation script invoked in the plan-review loop (e.g. `aggregate-findings.sh`), reducing operability for readers matching prose to code.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

---


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

