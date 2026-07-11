### [rejected] FINDING_7

**Rejected subtype:** dismissed (0 YES)

### FINDING_7: Reject duplicate keys in lane identity sidecars
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: Lane identity sidecar parsing uses first-wins `parse_kv`, unlike the materializer’s strict duplicate rejection. Conflicting duplicate keys can therefore pass if the first value matches the launch envelope. Use strict exact-key parsing consistent with `invariant_evidence._strict_kvs`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** dismissed (0 YES)

### FINDING_8: Make finalize lineage appends idempotent
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: `--finalize` unconditionally appends lineage rows, so duplicate finalize calls can inflate the next attempt while `fixer-rounds` retains the original attempt. Skip or reject duplicate `ATTEMPT`/`TIER`/`STEP` lineage rows before appending.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0
