### FINDING_1: RUNTIME promotion can certify non-fixed verdicts
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: major
- **Concern**: RUNTIME promotion and verified accounting do not pin a certifiable verdict set. A passing pytest or mapped harness could assign `RUNTIME` to `NOT_FIXED`, `REGRESSED`, `INCOMPLETE`, or `UNVERIFIABLE`, causing failed fixes to appear verified.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Pin promotion to the same fixed-family verdicts used elsewhere (CONFIRMED_FIXED, FIXED_CLEAR, FIXED_LIKELY). Absent or non-qualifying static verdicts keep their tier; runtime failure still downgrades to SUSPECT/RUNTIME.
  - From Cursor-Pragmatic: Pin one shared certifiable verdict set (at least `{FIXED_CLEAR, FIXED_LIKELY, CONFIRMED_FIXED}`) for both RUNTIME tier promotion and runtime-aware `_verified_issue`; add a negative test that passing runtime on `NOT_FIXED` does not promote or verify.


### FINDING_4: Anti-halt harness mapping uses the wrong prefix
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Concern**: Mapping `test-implement-anti-halt` to `skills/implement/` misses fixes that only touch `scripts/test-implement-anti-halt.sh`, so those changes resolve to the wrong harness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add an explicit `scripts/test-implement-anti-halt.sh` (or `scripts/test-implement-anti-halt`) → `test-implement-anti-halt` seed row, or otherwise ensure scripts-only anti-halt edits resolve that make target; extend harness-map tests for this path.


