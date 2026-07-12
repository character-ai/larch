### [rejected] FINDING_1

**Rejected subtype:** dismissed (0 YES)

### FINDING_1: Crash diagnostics are persisted before validation
- **Reviewer(s)**: cursor-specialist-correctness, dyn-dyn-crash-provenance
- **Severity**: major
- **Concern**: Crash diagnostics can fail or be committed before HEAD, salvage, and lineage validation, causing a valid salvage reship to become an operator bail and leaving inconsistent audit state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From dyn-dyn-crash-provenance: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** dismissed (0 YES)

### FINDING_2: UNAVAILABLE is misreported as exhaustion
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: An unavailable fixer tier is reported as exhausted, obscuring the actual operator-bail cause and potentially leaving lineage incomplete.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** dismissed (0 YES)

### FINDING_8: Crash-finalization failure reasons are too coarse
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: Distinct redaction, envelope, and lineage failures all emit `crash-finalization-failed`, hindering diagnosis and recovery.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** dismissed (0 YES)

### FINDING_9: Crash diagnostics lack untrusted-data framing
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: Vendor-controlled daemon-tail content is committed without an explicit boundary stating that it is untrusted evidence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_11: Timeout and orphaned outcomes lack coverage
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: Crash-finalization tests cover only numeric non-zero exits, not string daemon outcomes such as `timeout` and `orphaned`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** dismissed (0 YES)

### FINDING_12: Fail-closed crash finalization is untested
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: Malformed crash-finalization inputs lack pytest coverage for the required failure KVs and exit behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** dismissed (0 YES)

### FINDING_16: Fresh starts do not validate lineage identity
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: major
- **Concern**: A branch advance after retrying another tool can leave stale lineage associated with the same run ID, causing a tier to be skipped against a different diff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Validate lineage identity before selection; fail closed or explicitly reset on drift, with a wrapper regression test.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** dismissed (0 YES)

### FINDING_18: Non-salvage HEAD advances are dropped after crash
- **Reviewer(s)**: dyn-dyn-crash-provenance
- **Severity**: major
- **Concern**: A crash after dispatch advances HEAD with a `fixer-produced-change` commit, but crash finalization recognizes only the salvage subject and can operator-bail while dropping the fix.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-crash-provenance: Either broaden provenance (e.g. allow `fixer-produced-change` when `rev-list --count` is 1 and the parent matches `STARTING_HEAD`, with the same clean-worktree gate), or ensure `_dispatch` never returns `reship` until `_persist` succeeds so a post-dispatch crash cannot leave advanced `HEAD` on the crash-only salvage path.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_19

**Rejected subtype:** dismissed (0 YES)

### FINDING_19: Crash routing lacks a live-HEAD gate
- **Reviewer(s)**: dyn-dyn-crash-provenance
- **Severity**: major
- **Concern**: The non-zero `BGJOB_RC` wrapper path can emit stale `FINAL_HEAD` routing data without checking it against the live repository HEAD.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-crash-provenance: Parse `FINAL_HEAD` from crash-finalize stdout and apply the same live-`HEAD` equality gate before emitting routing KVs, or document and enforce an equivalent check in the Step 8 driver before `reship`.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0
