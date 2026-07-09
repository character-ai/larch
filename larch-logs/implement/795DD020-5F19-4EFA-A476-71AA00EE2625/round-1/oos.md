### FINDING_1: [OUT_OF_SCOPE] digest migration resets advisory counters
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing
- **Severity**: minor
- **Concern**: Changing the partition digest from Bash `cksum` to `sha256` will reset existing advisory counters once after upgrade. The reviewers treat that as an accepted one-time migration cost, not a runtime defect.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_2: [OUT_OF_SCOPE] unlocked read-modify-write can miss reminder counts
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: Concurrent hook invocations perform unlocked read-modify-write on the same state row, so overlapping reads can duplicate the reminder or miss the threshold entirely.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_4: [OUT_OF_SCOPE] hardlinked state leaf can be overwritten
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: State leaf files that are hardlinked can still be promoted with `os.replace`, which could overwrite an inode outside the state directory.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_5: [OUT_OF_SCOPE] untrusted TMPDIR can redirect state
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: `TMPDIR` is only required to be absolute, so a caller-controlled `TMPDIR` can point the hook at an untrusted temp tree instead of a trusted root.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_8: [OUT_OF_SCOPE] shard map missing new nodeids
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: New pytest nodeids are missing from the shard map, so CI falls back to round-robin sharding until the map is rebalanced.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_9: [OUT_OF_SCOPE] machine stdout registration not pinned
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: No explicit test pins hook anti-read-poll in `_MACHINE_STDOUT_KEYS`, so removing the registration could swallow threshold JSON under inherited quiet routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.
Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

