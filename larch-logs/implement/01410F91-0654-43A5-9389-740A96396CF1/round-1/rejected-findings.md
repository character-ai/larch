### [rejected] FINDING_1

**Rejected subtype:** dismissed (0 YES)

### FINDING_1: Bare-dir gap (#6137)
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: important
- **Concern**: A retained live marker directory can still hit the bare-directory deny path after the diagnosis carve-outs, including same-clone and `/private` alias cases.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** dismissed (0 YES)

### FINDING_2: `assert_deny` STEP verification (#6140)
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: important
- **Concern**: `assert_deny` should verify that the `STEP=` denial reason matches the step written by the nearest marker writer, or mismatched step attribution can slip through.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** dismissed (0 YES)

### FINDING_3: Marker-local clone identity (#6138)
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: important
- **Concern**: Clone identity resolution now needs to prefer marker-local `CLONE_PATH`, fall back to keepalive only when needed, and fail closed consistently when identity is unknown.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** dismissed (0 YES)

### FINDING_5: Unknown clone identity is not fail-closed for Monitor/TaskOutput
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: important
- **Concern**: Monitor/TaskOutput can still allow retained markers when clone identity is unknown, instead of failing closed as required by the plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** dismissed (0 YES)

### FINDING_6: Residual Bash manifest omission for parity harness
- **Reviewer(s)**: codex-specialist-edge-cases, cursor-specialist-testing
- **Severity**: important
- **Concern**: The new parity harness is not listed in the residual Bash manifest, so `lint-bash32` can skip it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** dismissed (0 YES)

### FINDING_7: Security policy stale for marker-local `CLONE_PATH` trust boundary
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: important
- **Concern**: `SECURITY.md` still documents the old `.larch-keepalive`-only trust boundary instead of the marker-local `CLONE_PATH` preference, fallback, and unknown-identity behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** dismissed (0 YES)

### FINDING_8: Missing parity harness in relevant-checks tuple
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: important
- **Concern**: The `bg-wait` relevant-checks tuple omits the parity harness, so clone-helper edits can pass local checks without running the drift guard.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** dismissed (0 YES)

### FINDING_9: `RETURN` trap breaks Bash 3.2 compatibility
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: important
- **Concern**: The harness uses a Bash 4.0+ `RETURN` trap, which conflicts with the stated Bash 3.2 compatibility.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_10

**Rejected subtype:** dismissed (0 YES)

### FINDING_10: Missing bare tmpdir-variable coverage in bg-poll guard tests
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: important
- **Concern**: The tests do not cover the bare tmpdir-variable path with conflicting marker-local and keepalive identities, so the marker-local resolver path remains unverified.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

