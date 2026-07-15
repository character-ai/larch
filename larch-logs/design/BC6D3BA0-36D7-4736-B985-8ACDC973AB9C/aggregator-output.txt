### FINDING_1: RUNTIME promotion can certify non-fixed verdicts
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: major
- **Concern**: RUNTIME promotion and verified accounting do not pin a certifiable verdict set. A passing pytest or mapped harness could assign `RUNTIME` to `NOT_FIXED`, `REGRESSED`, `INCOMPLETE`, or `UNVERIFIABLE`, causing failed fixes to appear verified.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Pin promotion to the same fixed-family verdicts used elsewhere (CONFIRMED_FIXED, FIXED_CLEAR, FIXED_LIKELY). Absent or non-qualifying static verdicts keep their tier; runtime failure still downgrades to SUSPECT/RUNTIME.
  - From Cursor-Pragmatic: Pin one shared certifiable verdict set (at least `{FIXED_CLEAR, FIXED_LIKELY, CONFIRMED_FIXED}`) for both RUNTIME tier promotion and runtime-aware `_verified_issue`; add a negative test that passing runtime on `NOT_FIXED` does not promote or verify.

### FINDING_2: Runtime overlay ordering can erase runtime verdicts
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Concern**: Applying runtime logic inside `_final_verdict_with_tier` conflicts with the later `DEEP_TRUNCATED` overlay, allowing deep truncation to replace a runtime `SUSPECT`/`RUNTIME` result.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Keep base verdict selection in _final_verdict_with_tier without runtime. Apply DEEP_TRUNCATED next. Call a dedicated _apply_runtime_overlay only after that block in render_report. State explicitly that runtime overlay must not live inside _final_verdict_with_tier.

### FINDING_3: HARNESS_MAP must support multiple targets per prefix
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Concern**: Seed rows can map one module prefix to multiple make targets, but a one-to-one dictionary silently discards all but one target.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Define HARNESS_MAP as an ordered tuple of (prefix, target) pairs per G-Cfg-1. Resolve every matching row, dedupe targets, and test the exact seed tuple shape.

### FINDING_4: Anti-halt harness mapping uses the wrong prefix
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Concern**: Mapping `test-implement-anti-halt` to `skills/implement/` misses fixes that only touch `scripts/test-implement-anti-halt.sh`, so those changes resolve to the wrong harness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add an explicit `scripts/test-implement-anti-halt.sh` (or `scripts/test-implement-anti-halt`) → `test-implement-anti-halt` seed row, or otherwise ensure scripts-only anti-halt edits resolve that make target; extend harness-map tests for this path.
