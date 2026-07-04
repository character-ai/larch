# Review Round 1

- Mode: `diff`
- 6 accepted, 0 rejected (1 neutral)

## Accepted Findings

### FINDING_1: stale payload sidecar on static plan-review fallback
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, codex-specialist-testing
- **Severity**: important
- **Concern**: Static plan-review renders can reuse a prior payload sidecar when a later render fails and falls back to a one-line prompt, inflating `payload_bytes` and skewing `scaffold_bytes` / panel telemetry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


### FINDING_3: invalid `payload_bytes` should clamp to zero, not env default
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: important
- **Concern**: An explicit malformed `payload_bytes` argument is incorrectly replaced by the environment default instead of being clamped to zero, so invalid input can be recorded as real payload and suppress `scaffold_bytes`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.


### FINDING_4: missing payload-threading regression tests across review pipeline
- **Reviewer(s)**: codex-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing
- **Severity**: important
- **Concern**: Several plan-required tests for payload/threading telemetry are still missing, leaving sidecar consumption, retry recomputation, env threading, dynamic scout folding, and implementer/waterfall telemetry paths without CI coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


### FINDING_5: rendering payload sidecar scenarios lack coverage
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: important
- **Concern**: Rendering payload sidecar coverage is incomplete; the remaining plan scenarios around truncation, path/body-file calibration, block handling, and failed writes are untested, so ledger-sized prompts can still miscount.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


### FINDING_6: `measure_panel_cost` ranking lacks a scaffold-byte regression test
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: important
- **Concern**: `measure_panel_cost` ranking behavior lacks a regression test that proves `scaffold_bytes` drives ordering, so a sort regression could mis-prioritize denser prompts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


### FINDING_7: legacy TSV headers are not migrated for 16-column rows
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: important
- **Concern**: Appending new 16-column telemetry rows into files with legacy 12-column headers can misalign `agent_file` and byte columns, corrupting appended `panel-prompt-sizes.tsv` data.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


