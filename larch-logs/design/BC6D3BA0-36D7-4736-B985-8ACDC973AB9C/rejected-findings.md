### [Plan Review] FINDING_2

### FINDING_2: Runtime overlay ordering can erase runtime verdicts
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Concern**: Applying runtime logic inside `_final_verdict_with_tier` conflicts with the later `DEEP_TRUNCATED` overlay, allowing deep truncation to replace a runtime `SUSPECT`/`RUNTIME` result.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Keep base verdict selection in _final_verdict_with_tier without runtime. Apply DEEP_TRUNCATED next. Call a dedicated _apply_runtime_overlay only after that block in render_report. State explicitly that runtime overlay must not live inside _final_verdict_with_tier.


### [Plan Review] FINDING_3

### FINDING_3: HARNESS_MAP must support multiple targets per prefix
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Concern**: Seed rows can map one module prefix to multiple make targets, but a one-to-one dictionary silently discards all but one target.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Define HARNESS_MAP as an ordered tuple of (prefix, target) pairs per G-Cfg-1. Resolve every matching row, dedupe targets, and test the exact seed tuple shape.


