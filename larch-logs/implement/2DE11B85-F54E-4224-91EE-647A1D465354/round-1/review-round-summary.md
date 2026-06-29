# Review Round 1

- Mode: `diff`
- 2 accepted, 3 rejected (1 neutral)

## Accepted Findings

### FINDING_3: marker writers do not clear terminal sentinels before re-arming
- **Reviewer(s)**: codex-generalist
- **Severity**: important
- **Concern**: New marker writers leave old terminal sentinels in place before writing `.bg-wait-active`, so reruns in the same tmpdir can make hooks treat a fresh wait as already complete.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generalist: Address the concern above.


### FINDING_4: explicit Step 4 probe validates against unrelated live markers
- **Reviewer(s)**: codex-generalist
- **Severity**: important
- **Concern**: An explicit `DESIGN_TMPDIR=<dir>` Step 4 sentinel probe is checked against every live marker directory instead of only its assigned target, so unrelated markers can block the documented recovery path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generalist: Address the concern above.


