### [rejected] FINDING_2

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_2: Untracked directories cause identity computation to fail
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, dyn-dyn-checks-identity
- **Severity**: minor
- **Concern**: A non-ignored untracked directory is rejected because identity computation accepts only regular files. This can abort the Step 3 and Step 6 launchers before checks start.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-checks-identity: Hash untracked directories deterministically (sorted listing + child metadata, or path-only with explicit directory marker) instead of erroring, and add regression coverage for `?? dir/` porcelain rows.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_5: `--force-checks` can rejoin a completed identity-valid skip result
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: In force mode, an identity-valid completed rejoin can still return a cached `skip-to-7a` result instead of running the checks composite. Repair re-entry with `--force-checks true` therefore may not actually force checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** dismissed (0 YES)

### FINDING_7: Missing `REPO_ROOT` failure path is untested
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: Composite checks behavior when persisted `REPO_ROOT` is missing or invalid lacks regression coverage and could fail opaquely.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add dispatch tests asserting exit 2 when REPO_ROOT is missing or invalid


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** dismissed (0 YES)

### FINDING_8: Matching failed results are rejoined without rerunning checks
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: An identity-valid completed result with `checks-failed` is reused after a failed run, so an unchanged tree returns the stale failure rather than rerunning checks. This is identified as existing behavior outside the current drift fix.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: No change unless product wants failed results never rejoin even when identity matches.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** dismissed (0 YES)

### FINDING_9: Integrity failures lack explicit operator routing
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: `identity-integrity-failed` is not explicitly routed in the Step 3 or Step 6 operator guidance, so users may see only a generic stall or `BGJOB_RC=1` without clear recovery instructions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Document routing or map integrity failure to a clear retry path in SKILL.md


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_10

**Rejected subtype:** dismissed (0 YES)

### FINDING_10: Live identity mismatch has limited diagnostics and cleanup guidance
- **Reviewer(s)**: cursor-specialist-correctness, dyn-dyn-checks-identity
- **Severity**: minor
- **Concern**: A live-registry identity mismatch exits fail-closed but leaves operators with only stderr or manual recovery requirements, including cases involving resumed state or legacy rows without identity fields.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Append bounded execution-issues entry or operator recovery note on live mismatch
  - From dyn-dyn-checks-identity: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_11: Binary git helper bypasses the injected Runner seam
- **Reviewer(s)**: cursor-specialist-correctness, dyn-dyn-checks-identity
- **Severity**: minor
- **Concern**: `_git_bytes_binary` invokes `subprocess.run` directly even though identity computation accepts an injected `Runner`, limiting testability and bypassing Runner-level timeout or failure simulation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Wrap in Runner with binary mode or document lint carve-out with regression coverage
  - From dyn-dyn-checks-identity: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** dismissed (0 YES)

### FINDING_12: Subprocess test helpers are duplicated
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: Stub-CLI helpers are duplicated across subprocess test modules, creating maintenance overhead without a direct functional regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Extract shared fixture helper in a follow-up


Vote tally: YES=0 NO=3 JUDGE_ERROR=0
